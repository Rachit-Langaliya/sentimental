"""
BERTopic wrapper — Phase 3.
Online/incremental mode: fits on accumulated posts, persists state to disk.
Assigns topics to posts and upserts the Topic table.

Requires USE_REAL_NLP=True and at least TOPIC_MIN_DOCS documents.
Falls back to keyword-based topic assignment when unavailable.
"""
from __future__ import annotations

import os
import pickle
import threading
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()

_lock = threading.Lock()
_model_instance = None


# ── Topic model loader ─────────────────────────────────────────────────────────

def _get_model():
    global _model_instance
    if _model_instance is not None:
        return _model_instance
    with _lock:
        if _model_instance is not None:
            return _model_instance
        try:
            _model_instance = _load_or_create()
            return _model_instance
        except Exception as exc:
            logger.warning("bertopic_init_failed", error=str(exc))
            return None


def _load_or_create():
    save_path = settings.TOPIC_MODEL_PATH
    if os.path.exists(f"{save_path}/topic_model.pkl"):
        logger.info("bertopic_loading_from_disk", path=save_path)
        with open(f"{save_path}/topic_model.pkl", "rb") as f:
            return pickle.load(f)
    return _create_fresh()


def _create_fresh():
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from umap import UMAP
    from sentence_transformers import SentenceTransformer

    embedding_model = SentenceTransformer(
        "paraphrase-multilingual-MiniLM-L12-v2",
        cache_folder=settings.HF_CACHE_DIR,
    )
    umap_model = UMAP(
        n_neighbors=10, n_components=5, min_dist=0.0,
        metric="cosine", random_state=42, low_memory=True,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=5, metric="euclidean",
        cluster_selection_method="eom", prediction_data=True,
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        language="multilingual",
        calculate_probabilities=True,
        verbose=False,
        min_topic_size=5,
        nr_topics="auto",
    )
    logger.info("bertopic_created_fresh")
    return topic_model


def _save_model(model) -> None:
    save_path = settings.TOPIC_MODEL_PATH
    os.makedirs(save_path, exist_ok=True)
    with open(f"{save_path}/topic_model.pkl", "wb") as f:
        pickle.dump(model, f)
    logger.info("bertopic_saved", path=save_path)


# ── Public API ─────────────────────────────────────────────────────────────────

async def fit_and_assign(texts: list[str], post_ids: list[int]) -> list[tuple[int, int, float]]:
    """
    Fit or update the BERTopic model on texts, then assign topics to post_ids.
    Returns list of (post_id, topic_id_in_bertopic, probability) tuples.
    Topics with id=-1 (outliers) are skipped.
    """
    if not settings.USE_REAL_NLP or len(texts) < settings.TOPIC_MIN_DOCS:
        return _fallback_assign(texts, post_ids)

    try:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, _fit_sync, texts, post_ids)
    except Exception as exc:
        logger.warning("bertopic_fit_failed", error=str(exc))
        return _fallback_assign(texts, post_ids)


def _fit_sync(texts: list[str], post_ids: list[int]) -> list[tuple[int, int, float]]:
    model = _get_model()
    if model is None:
        return _fallback_assign(texts, post_ids)

    try:
        topics, probs = model.fit_transform(texts)
    except Exception:
        # If already fitted, try transform-only
        try:
            topics, probs = model.transform(texts)
        except Exception as exc:
            logger.warning("bertopic_transform_failed", error=str(exc))
            return _fallback_assign(texts, post_ids)

    _save_model(model)

    results = []
    for post_id, topic_id, prob in zip(post_ids, topics, probs):
        if topic_id == -1:
            continue
        confidence = float(max(prob) if hasattr(prob, "__iter__") else prob)
        results.append((post_id, int(topic_id), round(confidence, 4)))
    return results


async def get_topic_info() -> list[dict]:
    """Return current topic representations for upserting to the Topic table."""
    if not settings.USE_REAL_NLP:
        return []
    try:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, _get_topic_info_sync)
    except Exception as exc:
        logger.warning("bertopic_get_info_failed", error=str(exc))
        return []


def _get_topic_info_sync() -> list[dict]:
    model = _get_model()
    if model is None or not hasattr(model, "get_topic_info"):
        return []
    info = model.get_topic_info()
    result = []
    for _, row in info.iterrows():
        tid = int(row["Topic"])
        if tid == -1:
            continue
        words = model.get_topic(tid)
        if not words:
            continue
        keywords = [w for w, _ in words[:10]]
        result.append({
            "bertopic_id": tid,
            "name": f"Topic {tid}: {', '.join(keywords[:3])}",
            "keywords": keywords,
        })
    return result


# ── Fallback: keyword-based assignment ────────────────────────────────────────

_KEYWORD_TOPICS = {
    0: ("Fuel & Energy Prices", ["petrol", "diesel", "lpg", "fuel", "price", "oil", "पेट्रोल", "ईंधन"]),
    1: ("AI & Technology Policy", ["ai", "artificial", "intelligence", "tech", "digital", "regulation"]),
    2: ("Agriculture & MSP", ["msp", "farmer", "kisan", "crop", "agriculture", "किसान", "खेती"]),
    3: ("Electric Vehicles", ["ev", "electric", "vehicle", "charging", "fame", "battery"]),
    4: ("Education Reform", ["nep", "education", "student", "exam", "university", "fee", "scholarship"]),
    5: ("Healthcare", ["health", "hospital", "medicine", "ayushman", "insurance", "pmjay"]),
    6: ("Employment & Jobs", ["job", "unemployment", "employment", "skill", "startup", "gig"]),
}


def _fallback_assign(texts: list[str], post_ids: list[int]) -> list[tuple[int, int, float]]:
    results = []
    for post_id, text in zip(post_ids, texts):
        lower = text.lower()
        best_topic, best_count = -1, 0
        for tid, (_, keywords) in _KEYWORD_TOPICS.items():
            count = sum(1 for kw in keywords if kw in lower)
            if count > best_count:
                best_count, best_topic = count, tid
        if best_topic >= 0:
            results.append((post_id, best_topic, round(0.4 + min(best_count * 0.1, 0.5), 3)))
    return results


def keyword_topic_names() -> dict[int, str]:
    return {tid: name for tid, (name, _) in _KEYWORD_TOPICS.items()}

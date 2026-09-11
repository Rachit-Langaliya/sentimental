"""
NLP Pipeline — Phase 3.
Lazy-loads transformer models on first use.
Falls back to rule-based mock when USE_REAL_NLP=False or models unavailable.

Model inventory:
  sentiment  : cardiffnlp/twitter-xlm-roberta-base-sentiment   (~1 GB)
  emotion    : j-hartmann/emotion-english-distilroberta-base    (~320 MB)
  irony      : cardiffnlp/twitter-roberta-base-irony            (~500 MB)
  embedding  : paraphrase-multilingual-MiniLM-L12-v2            (~120 MB)
"""
from __future__ import annotations

import os
import threading
from typing import Optional

import structlog

from app.core.config import settings
from app.services.language_detector import detect as detect_language

logger = structlog.get_logger()

# ── Model registry (lazy, thread-safe) ────────────────────────────────────────

_LOCK = threading.Lock()
_MODELS: dict = {}
_LOAD_ERRORS: dict[str, str] = {}

_HF_SENTIMENT = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_HF_EMOTION   = "j-hartmann/emotion-english-distilroberta-base"
_HF_IRONY     = "cardiffnlp/twitter-roberta-base-irony"
_HF_EMBED     = "paraphrase-multilingual-MiniLM-L12-v2"


def _load(name: str):
    if name in _MODELS:
        return _MODELS[name]
    if name in _LOAD_ERRORS:
        return None
    with _LOCK:
        if name in _MODELS:
            return _MODELS[name]
        try:
            os.environ.setdefault("TRANSFORMERS_CACHE", settings.HF_CACHE_DIR)
            if name == "sentiment":
                from transformers import pipeline
                _MODELS[name] = pipeline(
                    "text-classification", model=_HF_SENTIMENT,
                    top_k=None, device=-1, truncation=True, max_length=512,
                )
            elif name == "emotion":
                from transformers import pipeline
                _MODELS[name] = pipeline(
                    "text-classification", model=_HF_EMOTION,
                    top_k=None, device=-1, truncation=True, max_length=512,
                )
            elif name == "irony":
                from transformers import pipeline
                _MODELS[name] = pipeline(
                    "text-classification", model=_HF_IRONY,
                    top_k=None, device=-1, truncation=True, max_length=512,
                )
            elif name == "embedding":
                from sentence_transformers import SentenceTransformer
                _MODELS[name] = SentenceTransformer(
                    _HF_EMBED,
                    cache_folder=settings.HF_CACHE_DIR,
                )
            logger.info("nlp_model_loaded", model=name)
            return _MODELS[name]
        except Exception as exc:
            _LOAD_ERRORS[name] = str(exc)
            logger.warning("nlp_model_load_failed", model=name, error=str(exc))
            return None


def model_status() -> dict[str, dict]:
    """Return availability and load status for all models."""
    names = ["sentiment", "emotion", "irony", "embedding"]
    status = {}
    for n in names:
        if n in _MODELS:
            status[n] = {"loaded": True, "error": None}
        elif n in _LOAD_ERRORS:
            status[n] = {"loaded": False, "error": _LOAD_ERRORS[n]}
        else:
            status[n] = {"loaded": False, "error": None}
    status["use_real_nlp"] = settings.USE_REAL_NLP
    return status


# ── Label normalisers ──────────────────────────────────────────────────────────

_SENT_MAP = {
    "positive": "positive", "Positive": "positive",
    "negative": "negative", "Negative": "negative",
    "neutral":  "neutral",  "Neutral":  "neutral",
    "LABEL_0":  "negative", "LABEL_1":  "neutral", "LABEL_2":  "positive",
}

_IRONY_MAP = {
    "irony": True, "non_irony": False,
    "LABEL_0": False, "LABEL_1": True,
}


def _top(results: list[dict]) -> dict:
    return max(results, key=lambda x: x["score"])


# ── Real-model path ────────────────────────────────────────────────────────────

def _classify_real(texts: list[str]) -> list[dict]:
    """
    Run full transformer pipeline on a batch of texts.
    Returns list of dicts matching PostNLP columns.
    """
    sent_pipe = _load("sentiment")
    emot_pipe = _load("emotion")
    irony_pipe = _load("irony")
    embed_model = _load("embedding")

    batch_size = settings.NLP_BATCH_SIZE

    sentiments = sent_pipe(texts, batch_size=batch_size) if sent_pipe else None
    emotions   = emot_pipe(texts, batch_size=batch_size) if emot_pipe else None
    ironies    = irony_pipe(texts, batch_size=batch_size) if irony_pipe else None
    embeddings = embed_model.encode(texts, batch_size=batch_size, show_progress_bar=False) if embed_model else None

    results = []
    for i, text in enumerate(texts):
        # Sentiment
        if sentiments:
            sent_results = sentiments[i]
            top_sent = _top(sent_results)
            sentiment = _SENT_MAP.get(top_sent["label"], "neutral")
            sent_score = round(top_sent["score"], 4)
            # Support: positive_score
            pos_score = next((r["score"] for r in sent_results if _SENT_MAP.get(r["label"]) == "positive"), 0.0)
            support_score = round(pos_score, 4)
        else:
            sentiment, sent_score, support_score = "neutral", 0.5, 0.5

        # Emotion
        if emotions:
            emot_results = emotions[i]
            top_emot = _top(emot_results)
            emotion = top_emot["label"].lower()
            emot_score = round(top_emot["score"], 4)
            # Intensity: max(all emotion scores except neutral)
            intensity = round(max((r["score"] for r in emot_results if r["label"].lower() != "neutral"), default=0.0), 4)
        else:
            emotion, emot_score, intensity = "neutral", 0.5, 0.5

        # Irony/sarcasm
        if ironies:
            irony_results = ironies[i]
            top_irony = _top(irony_results)
            sarcasm_flag = _IRONY_MAP.get(top_irony["label"], False)
            sarcasm_conf = round(top_irony["score"], 4)
        else:
            sarcasm_flag, sarcasm_conf = False, 0.08

        # Embedding
        embedding = embeddings[i].tolist() if embeddings is not None else None

        results.append({
            "sentiment": sentiment,
            "sentiment_score": sent_score,
            "emotion": emotion,
            "emotion_score": emot_score,
            "support_score": support_score,
            "intensity": intensity,
            "sarcasm_flag": sarcasm_flag,
            "sarcasm_conf": sarcasm_conf,
            "model_version": "xlm-roberta-v1",
            "embedding": embedding,
        })

    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def process_batch(texts: list[str], languages: list[Optional[str]] = None) -> list[dict]:
    """
    Process a batch of texts.
    Uses real models if USE_REAL_NLP=True and models available.
    Falls back to rule-based mock otherwise.
    """
    if not texts:
        return []

    if settings.USE_REAL_NLP:
        try:
            return _classify_real(texts)
        except Exception as exc:
            logger.warning("real_nlp_failed_fallback", error=str(exc))

    # Mock fallback
    from app.services.nlp_mock import classify_post
    return [
        {**classify_post(t, stored_lang=l if languages else None), "embedding": None}
        for t, l in zip(texts, languages or [None] * len(texts))
    ]


def process_single(text: str, language: Optional[str] = None) -> dict:
    return process_batch([text], [language])[0]


def encode_texts(texts: list[str]) -> list[list[float]] | None:
    """
    Generate embeddings for a batch of texts.
    Returns None if embedding model unavailable.
    """
    if not settings.USE_REAL_NLP:
        return None
    model = _load("embedding")
    if model is None:
        return None
    try:
        vecs = model.encode(texts, batch_size=settings.NLP_BATCH_SIZE, show_progress_bar=False)
        return [v.tolist() for v in vecs]
    except Exception as exc:
        logger.warning("embedding_failed", error=str(exc))
        return None

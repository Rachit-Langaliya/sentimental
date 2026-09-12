"""
Pre-download all NLP transformer models to the HuggingFace cache.
Run once before starting the backend with USE_REAL_NLP=True:

    python -m app.scripts.download_models          # download all
    python -m app.scripts.download_models --check  # verify without re-downloading

Models (~2 GB total):
  - paraphrase-multilingual-MiniLM-L12-v2          (embeddings, 120 MB)
  - cardiffnlp/twitter-xlm-roberta-base-sentiment  (multilingual sentiment, ~1 GB)
  - j-hartmann/emotion-english-distilroberta-base  (emotion, 320 MB)
  - cardiffnlp/twitter-roberta-base-irony          (irony, 500 MB)
"""
from __future__ import annotations

import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.core.config import settings

CACHE = settings.HF_CACHE_DIR
os.makedirs(CACHE, exist_ok=True)

# (type, model_id, approx_mb)
MODELS: list[tuple[str, str, int]] = [
    ("sentence-transformers", "paraphrase-multilingual-MiniLM-L12-v2",          120),
    ("transformers",          "cardiffnlp/twitter-xlm-roberta-base-sentiment",  1020),
    ("transformers",          "j-hartmann/emotion-english-distilroberta-base",   320),
    ("transformers",          "cardiffnlp/twitter-roberta-base-irony",           500),
]
TOTAL_MB = sum(m[2] for m in MODELS)


def _free_gb(path: str) -> float:
    try:
        total, used, free = shutil.disk_usage(path)
        return free / (1024 ** 3)
    except Exception:
        return -1.0


def _cache_size_mb(path: str) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / (1024 ** 2)


def _bar(label: str, idx: int, total: int) -> None:
    filled = int(30 * idx / total)
    bar = "█" * filled + "░" * (30 - filled)
    print(f"\r  [{bar}] {idx}/{total} — {label}", end="", flush=True)


def _check_model_cached(model_id: str, cache: str) -> bool:
    """Return True if the model directory or safetensors files exist in cache."""
    slug = model_id.replace("/", "--")
    for root, dirs, files in os.walk(cache):
        if slug in root:
            safetensors = [f for f in files if f.endswith(".safetensors") or f.endswith(".bin")]
            if safetensors:
                return True
    return False


def check() -> None:
    print(f"\n=== Model Cache Check ===")
    print(f"Cache: {CACHE}")
    cache_mb = _cache_size_mb(CACHE)
    print(f"Current cache size: {cache_mb:.0f} MB\n")

    all_ok = True
    for typ, model_id, approx_mb in MODELS:
        cached = _check_model_cached(model_id, CACHE)
        status = "✓ present" if cached else "✗ missing"
        print(f"  {status:12s}  {model_id}  (~{approx_mb} MB)")
        if not cached:
            all_ok = False

    print()
    if all_ok:
        print("All models present. You can set USE_REAL_NLP=True.")
    else:
        print("Some models missing. Run without --check to download them.")


def download() -> None:
    free = _free_gb(CACHE)
    needed_gb = TOTAL_MB / 1024

    print(f"\n=== SIH NLP Model Downloader ===")
    print(f"Cache:      {CACHE}")
    if free >= 0:
        print(f"Disk free:  {free:.1f} GB  (need ~{needed_gb:.1f} GB)")
        if free < needed_gb * 1.2:
            print(f"\nWARNING: Low disk space. Need ~{needed_gb:.1f} GB free.")
            if free < needed_gb:
                print("ERROR: Not enough disk space. Aborting.")
                sys.exit(1)
    print(f"Total size: ~{TOTAL_MB} MB across {len(MODELS)} models\n")

    overall_start = time.time()

    # ── [1/4] Sentence Transformers embedding model ───────────────────────────
    typ, name, approx_mb = MODELS[0]
    print(f"[1/{len(MODELS)}] {name}  (~{approx_mb} MB)")
    t0 = time.time()
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(name, cache_folder=CACHE)
        print(f"       ✓ done  ({time.time()-t0:.0f}s)")
    except Exception as exc:
        print(f"       ✗ FAILED: {exc}")

    # ── [2–4] HuggingFace classification models ───────────────────────────────
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError:
        print("ERROR: transformers not installed. Run: pip install transformers")
        sys.exit(1)

    for i, (_, model_id, approx_mb) in enumerate(MODELS[1:], start=2):
        print(f"[{i}/{len(MODELS)}] {model_id}  (~{approx_mb} MB)")
        t0 = time.time()
        try:
            AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE)
            print(f"       tokenizer ✓", end="")
            AutoModelForSequenceClassification.from_pretrained(model_id, cache_dir=CACHE)
            print(f"  weights ✓  ({time.time()-t0:.0f}s)")
        except Exception as exc:
            print(f"\n       ✗ FAILED: {exc}")

    elapsed = time.time() - overall_start
    cache_mb = _cache_size_mb(CACHE)
    print(f"\n=== Complete in {elapsed:.0f}s  |  Cache now: {cache_mb:.0f} MB ===")
    print("Set USE_REAL_NLP=True in .env to activate real NLP pipelines.")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        download()

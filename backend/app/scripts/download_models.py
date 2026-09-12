"""
Pre-download all NLP transformer models to the HuggingFace cache.
Run once before starting the backend with USE_REAL_NLP=True:

    python -m app.scripts.download_models

Models downloaded (~2 GB total):
  - paraphrase-multilingual-MiniLM-L12-v2   (sentence embeddings, 384-dim)
  - cardiffnlp/twitter-xlm-roberta-base-sentiment  (multilingual sentiment)
  - j-hartmann/emotion-english-distilroberta-base  (7-class emotion)
  - cardiffnlp/twitter-roberta-base-irony          (sarcasm / irony)
"""
import os
import sys

# Allow running as `python -m app.scripts.download_models` from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.core.config import settings

CACHE = settings.HF_CACHE_DIR
os.makedirs(CACHE, exist_ok=True)

MODELS = [
    ("sentence-transformers", "paraphrase-multilingual-MiniLM-L12-v2"),
    ("transformers",          "cardiffnlp/twitter-xlm-roberta-base-sentiment"),
    ("transformers",          "j-hartmann/emotion-english-distilroberta-base"),
    ("transformers",          "cardiffnlp/twitter-roberta-base-irony"),
]


def download():
    print(f"Downloading to cache: {CACHE}\n")

    # Sentence transformer
    lib, name = MODELS[0]
    print(f"[1/4] {name} (sentence-transformers)…")
    from sentence_transformers import SentenceTransformer
    SentenceTransformer(name, cache_folder=CACHE)
    print("      ✓ done")

    # Three transformer models
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    for i, (_, model_id) in enumerate(MODELS[1:], start=2):
        print(f"[{i}/4] {model_id}…")
        AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE)
        AutoModelForSequenceClassification.from_pretrained(model_id, cache_dir=CACHE)
        print("      ✓ done")

    print("\nAll models downloaded. Set USE_REAL_NLP=True in .env to activate them.")


if __name__ == "__main__":
    download()

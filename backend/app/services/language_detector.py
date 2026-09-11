"""
Language detection — Phase 3.
Primary: Unicode script detection for Indian languages (fast, zero dependency).
Fallback: langdetect for Latin-script languages.
Returns ISO 639-1 codes: en / hi / ta / te / kn / ml / bn / mr / gu / pa / ur
"""
import re
from functools import lru_cache

# Unicode block ranges for Indian scripts
_SCRIPT_RANGES = [
    (r"[ऀ-ॿ]", "hi"),   # Devanagari  → Hindi / Marathi
    (r"[஀-௿]", "ta"),   # Tamil
    (r"[ఀ-౿]", "te"),   # Telugu
    (r"[ಀ-೿]", "kn"),   # Kannada
    (r"[ഀ-ൿ]", "ml"),   # Malayalam
    (r"[ঀ-৿]", "bn"),   # Bengali
    (r"[઀-૿]", "gu"),   # Gujarati
    (r"[਀-੿]", "pa"),   # Gurmukhi (Punjabi)
    (r"[؀-ۿ]", "ur"),   # Arabic → Urdu
]

_DEVANAGARI_MARATHI = re.compile(r"\b(आहे|मराठी|महाराष्ट्र|आणि|हे|ते|त्यांनी)\b")


def detect(text: str) -> str:
    """
    Detect language from text. Returns ISO 639-1 code.
    Fast path: script heuristic (no imports).
    Slow path: langdetect for Latin-only text.
    """
    if not text or len(text.strip()) < 4:
        return "en"

    # Script detection
    for pattern, lang_code in _SCRIPT_RANGES:
        if re.search(pattern, text):
            if lang_code == "hi" and _DEVANAGARI_MARATHI.search(text):
                return "mr"
            return lang_code

    # Latin-script → langdetect
    try:
        from langdetect import detect as _ld_detect
        from langdetect.lang_detect_exception import LangDetectException
        try:
            result = _ld_detect(text)
            return result[:2]  # take first 2 chars (e.g. "en-US" → "en")
        except (LangDetectException, Exception):
            return "en"
    except ImportError:
        return "en"

"""
Mock NLP service for Phase 2.
Applies fast rule-based classification to ingested posts.
Phase 3 replaces this with XLM-RoBERTa / distilroberta-emotions.
"""
import re
from typing import Optional

# ── Keyword banks ─────────────────────────────────────────────────────────────

_POS_EN = {
    "good", "great", "excellent", "happy", "support", "helpful", "benefit", "growth",
    "success", "thank", "welcome", "improve", "positive", "relief", "hope", "strong",
    "progress", "opportunity", "invest", "launch", "initiative", "reform", "boost",
    "encourage", "develop", "flourish", "finally", "exciting", "love", "appreciate",
}
_NEG_EN = {
    "bad", "terrible", "hate", "protest", "burden", "fail", "corrupt", "expensive",
    "suffer", "crisis", "concern", "anger", "unacceptable", "fraud", "injustice",
    "increase", "hike", "problem", "issue", "hurt", "damage", "collapse", "decline",
    "unemployment", "poverty", "fail", "reject", "oppose", "fear", "worry", "worse",
}
_POS_HI = {"अच्छा", "बेहतर", "खुशी", "समर्थन", "फायदा", "स्वागत", "उम्मीद", "सफल", "धन्यवाद", "विकास"}
_NEG_HI = {"बुरा", "विरोध", "समस्या", "परेशान", "भ्रष्ट", "महंगाई", "कठिन", "नाराज", "गलत", "बोझ"}

_EMOTION_ANGER = {"hate", "unacceptable", "fraud", "corrupt", "injustice", "विरोध", "नाराज", "गलत"}
_EMOTION_JOY = {"happy", "love", "excited", "great", "celebrate", "खुशी", "बेहतर", "स्वागत"}
_EMOTION_FEAR = {"fear", "worry", "concern", "crisis", "dangerous", "scared", "परेशान", "डर"}
_EMOTION_SADNESS = {"sad", "suffer", "unfortunate", "poor", "poverty", "दुख", "कठिन"}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\wऀ-ॿ஀-௿ఀ-౿]+", text.lower())
    return set(words)


def _detect_language(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    if re.search(r"[஀-௿]", text):
        return "ta"
    if re.search(r"[ఀ-౿]", text):
        return "te"
    return "en"


def classify_post(text: str, stored_lang: Optional[str] = None) -> dict:
    """
    Returns a dict matching PostNLP columns.
    """
    tokens = _tokenize(text)
    lang = stored_lang or _detect_language(text)

    pos_hits = len(tokens & (_POS_EN | _POS_HI))
    neg_hits = len(tokens & (_NEG_EN | _NEG_HI))
    total = max(len(tokens), 1)

    pos_score = min(1.0, pos_hits / (total ** 0.5) * 3)
    neg_score = min(1.0, neg_hits / (total ** 0.5) * 3)
    intensity = min(1.0, (pos_hits + neg_hits) / (total ** 0.5) * 2)

    if pos_score > neg_score + 0.15:
        sentiment, sent_score = "positive", round(0.55 + pos_score * 0.4, 3)
        support_score = round(min(1.0, 0.5 + pos_score * 0.5), 3)
    elif neg_score > pos_score + 0.10:
        sentiment, sent_score = "negative", round(0.55 + neg_score * 0.4, 3)
        support_score = round(max(0.0, 0.3 - neg_score * 0.3), 3)
    else:
        sentiment, sent_score = "neutral", round(0.52 + abs(pos_score - neg_score) * 0.2, 3)
        support_score = 0.45

    # Emotion
    emotion = "neutral"
    if tokens & _EMOTION_ANGER:
        emotion = "anger"
    elif tokens & _EMOTION_JOY:
        emotion = "joy"
    elif tokens & _EMOTION_FEAR:
        emotion = "fear"
    elif tokens & _EMOTION_SADNESS:
        emotion = "sadness"

    return {
        "sentiment": sentiment,
        "sentiment_score": round(sent_score, 3),
        "emotion": emotion,
        "emotion_score": round(0.55 + intensity * 0.3, 3),
        "support_score": round(support_score, 3),
        "intensity": round(intensity, 3),
        "sarcasm_flag": False,
        "sarcasm_conf": 0.08,
        "model_version": "rule-based-v2",
    }

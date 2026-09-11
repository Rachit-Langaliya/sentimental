from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.api.deps import CurrentUser, DB
from app.schemas.schemas import SentimentAnalyzeRequest, SentimentResult, SentimentTimeline, TimePoint

router = APIRouter()


@router.post("/analyze", response_model=SentimentResult)
async def analyze_text(body: SentimentAnalyzeRequest, current_user: CurrentUser):
    """
    Analyze a single text for sentiment, emotion, and intensity.
    Phase 1: returns mock result with detected language stub.
    Phase 3: will route to real NLP pipeline.
    """
    # Mock detection for Phase 1 — real models wired in Phase 3
    text_lower = body.text.lower()
    if any(w in text_lower for w in ["great", "good", "love", "excellent", "happy", "best"]):
        sentiment, score = "positive", 0.82
    elif any(w in text_lower for w in ["bad", "worst", "hate", "terrible", "sad", "angry"]):
        sentiment, score = "negative", 0.79
    else:
        sentiment, score = "neutral", 0.61

    return SentimentResult(
        text=body.text,
        language=body.language or "en",
        sentiment=sentiment,
        sentiment_score=score,
        emotion="neutral",
        emotion_score=0.55,
        intensity=0.6,
        sarcasm_flag=False,
        sarcasm_conf=0.12,
        epistemic_note="model-inferred [Phase 1 mock — real models in Phase 3]",
    )


@router.get("/timeline", response_model=SentimentTimeline)
async def sentiment_timeline(current_user: CurrentUser, platform: str | None = None, hours: int = 24):
    """Overall sentiment timeline. Phase 1: mock data."""
    import math, random

    now = datetime.now(timezone.utc)
    points = []
    for i in range(hours, 0, -1):
        t = now - timedelta(hours=i)
        pos = 0.30 + 0.04 * math.sin(i / 3)
        neg = 0.26 + random.uniform(-0.03, 0.03)
        neu = 1.0 - pos - neg
        points.append(TimePoint(timestamp=t, positive=round(pos, 3), neutral=round(max(0, neu), 3), negative=round(neg, 3)))

    return SentimentTimeline(points=points, platform=platform)

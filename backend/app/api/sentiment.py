from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.api.deps import CurrentUser, DB
from app.schemas.schemas import SentimentAnalyzeRequest, SentimentResult, SentimentTimeline, TimePoint

router = APIRouter()


@router.post("/analyze", response_model=SentimentResult)
async def analyze_text(body: SentimentAnalyzeRequest, current_user: CurrentUser):
    """
    Analyze a single text for sentiment, emotion, intensity, and sarcasm.
    Routes to real transformer pipeline when USE_REAL_NLP=True; falls back to rule-based mock.
    """
    from app.services.nlp_pipeline import process_batch
    from app.services.language_detector import detect as detect_lang

    language = body.language or detect_lang(body.text)
    results = process_batch([body.text], [language])
    r = results[0]

    model_note = r.get("model_version", "rule-based-v2")
    epistemic = f"model-inferred [{model_note}]"
    if r.get("sarcasm_flag"):
        epistemic += " [sarcasm-flagged: treat with caution]"

    return SentimentResult(
        text=body.text,
        language=language,
        sentiment=r["sentiment"],
        sentiment_score=round(r["sentiment_score"], 4),
        emotion=r.get("emotion"),
        emotion_score=round(r["emotion_score"], 4) if r.get("emotion_score") else None,
        intensity=round(r["intensity"], 4) if r.get("intensity") else None,
        sarcasm_flag=r.get("sarcasm_flag", False),
        sarcasm_conf=round(r["sarcasm_conf"], 4) if r.get("sarcasm_conf") else None,
        epistemic_note=epistemic,
    )


@router.get("/timeline", response_model=SentimentTimeline)
async def sentiment_timeline(current_user: CurrentUser, db: DB, platform: str | None = None, hours: int = 24):
    """Overall sentiment timeline from real NLP data; falls back to synthetic if insufficient data."""
    from sqlalchemy import func, select, case
    from app.models.models import PostNLP, RawPost, Platform

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)

    query = (
        select(
            func.date_trunc("hour", RawPost.post_ts).label("bucket"),
            func.avg(case((PostNLP.sentiment == "positive", 1.0), else_=0.0)).label("pos"),
            func.avg(case((PostNLP.sentiment == "negative", 1.0), else_=0.0)).label("neg"),
            func.count(PostNLP.post_id).label("cnt"),
        )
        .join(PostNLP, PostNLP.post_id == RawPost.id)
        .where(RawPost.post_ts >= since)
    )

    if platform:
        plat_r = await db.execute(select(Platform).where(Platform.name == platform))
        plat = plat_r.scalar_one_or_none()
        if plat:
            query = query.where(RawPost.platform_id == plat.id)

    query = query.group_by("bucket").order_by("bucket")
    rows = (await db.execute(query)).all()

    # Need at least 3 data points for a meaningful chart; otherwise fall back to synthetic
    if len(rows) >= 3:
        points = []
        for row in rows:
            pos = float(row.pos or 0)
            neg = float(row.neg or 0)
            neu = max(0.0, 1.0 - pos - neg)
            points.append(TimePoint(timestamp=row.bucket, positive=round(pos, 3), neutral=round(neu, 3), negative=round(neg, 3)))
    else:
        import math, random
        points = []
        for i in range(hours, 0, -1):
            t = now - timedelta(hours=i)
            pos = 0.30 + 0.04 * math.sin(i / 3)
            neg = 0.26 + random.uniform(-0.03, 0.03)
            neu = 1.0 - pos - neg
            points.append(TimePoint(timestamp=t, positive=round(pos, 3), neutral=round(max(0, neu), 3), negative=round(neg, 3)))

    return SentimentTimeline(points=points, platform=platform)

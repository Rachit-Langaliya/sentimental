from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, case
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DB
from app.models.models import DemographicSegment, Persona, PostNLP, RawPost
from app.schemas.schemas import PersonaRead, PersonaRegenerateResult, SegmentDetail, SegmentList, SegmentSummary

router = APIRouter()


@router.get("/", response_model=SegmentList)
async def list_segments(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(DemographicSegment).order_by(DemographicSegment.evidence_count.desc())
    )
    segments = result.scalars().all()
    items = [SegmentSummary.model_validate(s) for s in segments]
    return SegmentList(items=items, total=len(items))


@router.get("/{segment_id}", response_model=SegmentDetail)
async def get_segment(segment_id: int, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(DemographicSegment)
        .options(selectinload(DemographicSegment.personas))
        .where(DemographicSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    detail = SegmentDetail.model_validate(segment)
    if segment.personas:
        latest = max(segment.personas, key=lambda p: p.generated_at)
        detail.persona = PersonaRead.model_validate(latest)
    return detail


@router.get("/{segment_id}/timeline")
async def segment_timeline(segment_id: int, current_user: CurrentUser, db: DB, days: int = 7):
    """
    Daily sentiment breakdown for posts from this segment's dominant language group.
    Falls back to synthetic curve when insufficient data.
    """
    seg_r = await db.execute(
        select(DemographicSegment).where(DemographicSegment.id == segment_id)
    )
    segment = seg_r.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Query posts matching this segment's dominant language
    lang_code = _lang_name_to_code(segment.dominant_language)
    query = (
        select(
            func.date_trunc("day", RawPost.post_ts).label("bucket"),
            func.avg(case((PostNLP.sentiment == "positive", 1.0), else_=0.0)).label("pos"),
            func.avg(case((PostNLP.sentiment == "negative", 1.0), else_=0.0)).label("neg"),
            func.count(PostNLP.post_id).label("cnt"),
        )
        .join(PostNLP, PostNLP.post_id == RawPost.id)
        .where(RawPost.post_ts >= since)
    )
    if lang_code:
        query = query.where(RawPost.language == lang_code)
    query = query.group_by("bucket").order_by("bucket")

    rows = (await db.execute(query)).all()

    if len(rows) >= 3:
        points = []
        for row in rows:
            pos = float(row.pos or 0)
            neg = float(row.neg or 0)
            neu = max(0.0, 1.0 - pos - neg)
            points.append({
                "date": row.bucket.isoformat(),
                "positive": round(pos, 3),
                "neutral": round(neu, 3),
                "negative": round(neg, 3),
                "count": int(row.cnt),
            })
    else:
        # Synthetic fallback seeded from segment's sentiment_profile
        import math, random
        sp = segment.sentiment_profile or {"positive": 0.35, "neutral": 0.40, "negative": 0.25}
        base_pos = sp.get("positive", 0.35)
        base_neg = sp.get("negative", 0.25)
        points = []
        for i in range(days, 0, -1):
            t = now - timedelta(days=i)
            pos = max(0, min(1, base_pos + 0.03 * math.sin(i) + random.uniform(-0.02, 0.02)))
            neg = max(0, min(1, base_neg + random.uniform(-0.02, 0.02)))
            neu = max(0, 1.0 - pos - neg)
            points.append({
                "date": t.date().isoformat(),
                "positive": round(pos, 3),
                "neutral": round(neu, 3),
                "negative": round(neg, 3),
                "count": 0,
            })

    return {"segment_id": segment_id, "points": points}


@router.post("/{segment_id}/regenerate-persona", response_model=PersonaRegenerateResult)
async def regenerate_persona(segment_id: int, current_user: CurrentUser, db: DB):
    """
    Use the local Ollama LLM to regenerate the persona summary for a segment.
    Saves the new persona to the database and returns it.
    Requires Ollama to be running with the configured model.
    """
    from app.services import ollama_client

    seg_r = await db.execute(
        select(DemographicSegment).where(DemographicSegment.id == segment_id)
    )
    segment = seg_r.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    if not await ollama_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available. Start it with: docker compose --profile llm up -d",
        )

    summary = await ollama_client.generate_persona({
        "name": segment.name,
        "dominant_language": segment.dominant_language,
        "size_estimate": segment.size_estimate,
        "topic_prefs": segment.topic_prefs,
        "sentiment_profile": segment.sentiment_profile,
        "geo_distribution": segment.geo_distribution,
    })

    if not summary:
        raise HTTPException(status_code=503, detail="LLM generation failed — model may not be pulled yet. Call POST /ollama/warm first.")

    # Persist as a new Persona row
    existing_r = await db.execute(
        select(Persona).where(Persona.segment_id == segment_id)
    )
    existing = existing_r.scalars().all()

    # Keep at most 2 historical personas, add the new one
    if len(existing) >= 3:
        oldest = min(existing, key=lambda p: p.generated_at)
        await db.delete(oldest)

    # Get existing interests from latest persona
    interests = None
    if existing:
        latest = max(existing, key=lambda p: p.generated_at)
        interests = latest.interests

    new_persona = Persona(
        segment_id=segment_id,
        summary=summary,
        interests=interests,
        confidence=round(0.70 + 0.15 * (segment.confidence or 0.7), 3),
        evidence_json={"generated_by": "ollama", "model": "local-llm"},
    )
    db.add(new_persona)
    await db.commit()

    return PersonaRegenerateResult(
        segment_id=segment_id,
        persona_summary=summary,
        generated_by="local-llm",
    )


@router.post("/trigger-segmentation")
async def trigger_segmentation(current_user: CurrentUser):
    """Manually queue one segmentation cycle."""
    from app.workers.tasks import run_segmentation
    task = run_segmentation.delay()
    return {"status": "queued", "task_id": task.id}


def _lang_name_to_code(lang_name: str | None) -> str | None:
    _MAP = {
        "English": "en", "Hindi": "hi", "Tamil": "ta", "Telugu": "te",
        "Bengali": "bn", "Marathi": "mr", "Gujarati": "gu",
        "Kannada": "kn", "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur",
    }
    if not lang_name:
        return None
    return _MAP.get(lang_name)

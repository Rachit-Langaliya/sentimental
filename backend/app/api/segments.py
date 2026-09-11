from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DB
from app.models.models import DemographicSegment, Persona
from app.schemas.schemas import PersonaRead, SegmentDetail, SegmentList, SegmentSummary

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
async def segment_timeline(segment_id: int, current_user: CurrentUser, db: DB):
    # Phase 3 will wire real NLP data. Returns mock for Phase 1.
    from datetime import datetime, timedelta, timezone
    import math, random

    now = datetime.now(timezone.utc)
    points = []
    for i in range(7, 0, -1):
        t = now - timedelta(days=i)
        pos = 0.30 + 0.04 * math.sin(i)
        neg = 0.28 + random.uniform(-0.03, 0.03)
        neu = 1.0 - pos - neg
        points.append({"date": t.isoformat(), "positive": round(pos, 3), "neutral": round(max(0, neu), 3), "negative": round(neg, 3)})
    return {"segment_id": segment_id, "points": points}

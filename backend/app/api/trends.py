from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.models import Trend
from app.schemas.schemas import TrendDetail, TrendList, TrendSummary

router = APIRouter()


@router.get("/", response_model=TrendList)
async def list_trends(current_user: CurrentUser, db: DB, limit: int = 20):
    result = await db.execute(
        select(Trend).order_by(Trend.trend_score.desc()).limit(limit)
    )
    trends = result.scalars().all()
    items = [TrendSummary.model_validate(t) for t in trends]
    return TrendList(items=items, total=len(items))


@router.get("/emerging", response_model=TrendList)
async def emerging_trends(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Trend).where(Trend.is_emerging == True).order_by(Trend.velocity.desc())
    )
    trends = result.scalars().all()
    items = [TrendSummary.model_validate(t) for t in trends]
    return TrendList(items=items, total=len(items))


@router.get("/{trend_id}", response_model=TrendDetail)
async def get_trend(trend_id: int, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Trend).where(Trend.id == trend_id))
    trend = result.scalar_one_or_none()
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    return TrendDetail.model_validate(trend)

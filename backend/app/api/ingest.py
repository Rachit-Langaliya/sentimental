"""
Ingestion management API.
Exposes connector health status, per-platform stats, and a manual trigger.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB
from app.models.models import PostNLP, RawPost, Platform
from app.schemas.schemas import ConnectorStatusSchema, IngestionStats, PlatformIngestionStat

router = APIRouter()


@router.get("/status", response_model=list[ConnectorStatusSchema])
async def connector_status(current_user: CurrentUser):
    """Health-check all connectors and return their status."""
    from app.connectors.registry import registry
    statuses = await registry.health_check_all()
    return [
        ConnectorStatusSchema(
            platform=s.platform,
            mode=s.mode,
            is_healthy=s.is_healthy,
            posts_ingested_total=s.posts_ingested_total,
            last_ingested_at=s.last_ingested_at,
            error=s.error,
        )
        for s in statuses
    ]


@router.post("/trigger")
async def trigger_ingestion(current_user: CurrentUser):
    """
    Manually trigger one ingestion cycle (demo use).
    Queues the Celery task so it runs asynchronously.
    """
    from app.workers.tasks import run_platform_ingestion
    task = run_platform_ingestion.delay()
    return {"status": "queued", "task_id": task.id}


@router.get("/stats", response_model=IngestionStats)
async def ingestion_stats(current_user: CurrentUser, db: DB):
    """Per-platform post counts and NLP coverage."""
    plat_r = await db.execute(select(Platform))
    platforms = plat_r.scalars().all()

    stats: list[PlatformIngestionStat] = []
    for p in platforms:
        count_r = await db.execute(
            select(func.count(RawPost.id)).where(RawPost.platform_id == p.id)
        )
        total = count_r.scalar() or 0

        # NLP coverage for this platform
        nlp_r = await db.execute(
            select(func.count(PostNLP.post_id))
            .join(RawPost, RawPost.id == PostNLP.post_id)
            .where(RawPost.platform_id == p.id)
        )
        nlp_done = nlp_r.scalar() or 0
        nlp_pct = round(nlp_done / total, 3) if total > 0 else 0.0

        stats.append(PlatformIngestionStat(
            platform=p.name,
            display_name=p.display_name,
            total_posts=total,
            nlp_processed=nlp_done,
            nlp_coverage=nlp_pct,
            color=p.color,
        ))

    total_posts_r = await db.execute(select(func.count(RawPost.id)))
    total_posts = total_posts_r.scalar() or 0

    total_nlp_r = await db.execute(select(func.count(PostNLP.post_id)))
    total_nlp = total_nlp_r.scalar() or 0

    return IngestionStats(
        total_posts=total_posts,
        nlp_processed=total_nlp,
        nlp_coverage=round(total_nlp / total_posts, 3) if total_posts > 0 else 0.0,
        per_platform=stats,
        generated_at=datetime.now(timezone.utc),
    )

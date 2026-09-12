import asyncio

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


# ── Ingestion task ─────────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.run_platform_ingestion", bind=True, max_retries=3)
def run_platform_ingestion(self):
    """Fan-out ingestion across all platform connectors, then trigger NLP."""
    try:
        from app.connectors.registry import registry
        results = asyncio.run(registry.ingest_all())
        total = sum(results.values())
        logger.info("platform_ingestion_done", per_platform=results, total=total)
        if total > 0:
            process_nlp_batch.delay(limit=min(total * 4, 300))
        return {"status": "ok", "per_platform": results, "total": total}
    except Exception as exc:
        logger.error("platform_ingestion_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# ── NLP task ───────────────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.process_nlp_batch", bind=True, max_retries=2)
def process_nlp_batch(self, limit: int = 100):
    """
    Process unanalysed posts through the NLP pipeline (Phase 3: real models; fallback: rule-based).
    Writes results to post_nlp and post_embeddings tables.
    """
    try:
        count = asyncio.run(_run_nlp_batch(limit))
        logger.info("nlp_batch_done", processed=count)
        return {"status": "ok", "processed": count}
    except Exception as exc:
        logger.error("nlp_batch_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=15)


async def _run_nlp_batch(limit: int) -> int:
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.models import PostEmbedding, PostNLP, RawPost
    from app.services.nlp_pipeline import process_batch

    async with SessionLocal() as db:
        stmt = (
            select(RawPost)
            .outerjoin(PostNLP, RawPost.id == PostNLP.post_id)
            .where(PostNLP.post_id.is_(None))
            .order_by(RawPost.ingested_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        posts = result.scalars().all()

        if not posts:
            return 0

        texts = [p.content or "" for p in posts]
        langs = [p.language for p in posts]

        nlp_results = process_batch(texts, langs)

        nlp_rows, embed_rows = [], []
        for post, nlp in zip(posts, nlp_results):
            nlp_rows.append(PostNLP(
                post_id=post.id,
                sentiment=nlp["sentiment"],
                sentiment_score=nlp["sentiment_score"],
                emotion=nlp["emotion"],
                emotion_score=nlp["emotion_score"],
                support_score=nlp["support_score"],
                intensity=nlp["intensity"],
                sarcasm_flag=nlp["sarcasm_flag"],
                sarcasm_conf=nlp["sarcasm_conf"],
                model_version=nlp["model_version"],
            ))
            if nlp.get("embedding") is not None:
                embed_rows.append(PostEmbedding(
                    post_id=post.id,
                    embedding_json=nlp["embedding"],
                ))

        db.add_all(nlp_rows)
        if embed_rows:
            db.add_all(embed_rows)
        await db.commit()
        return len(nlp_rows)


# ── Topic modeling task ────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.run_topic_modeling", bind=True, max_retries=2)
def run_topic_modeling(self, limit: int = 500):
    """
    Fit/update BERTopic on recent posts and persist topic assignments.
    Also upserts Topic table rows for discovered topics.
    """
    try:
        count = asyncio.run(_run_topic_modeling(limit))
        logger.info("topic_modeling_done", assigned=count)
        return {"status": "ok", "assigned": count}
    except Exception as exc:
        logger.error("topic_modeling_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


async def _run_topic_modeling(limit: int) -> int:
    from datetime import timedelta, timezone
    from datetime import datetime
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.models import PostTopic, RawPost, Topic
    from app.services.topic_modeler import fit_and_assign, get_topic_info, keyword_topic_names

    async with SessionLocal() as db:
        # Posts without topic assignments
        window = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = (
            select(RawPost)
            .outerjoin(PostTopic, RawPost.id == PostTopic.post_id)
            .where(PostTopic.post_id.is_(None))
            .where(RawPost.post_ts >= window)
            .limit(limit)
        )
        result = await db.execute(stmt)
        posts = result.scalars().all()

        if not posts:
            return 0

        texts = [p.content or "" for p in posts]
        post_ids = [p.id for p in posts]

        assignments = await fit_and_assign(texts, post_ids)

        # Ensure Topic rows exist for all bertopic_ids
        topic_info = await get_topic_info()
        names = keyword_topic_names()
        bertopic_to_db_id: dict[int, int] = {}

        for info in topic_info:
            tid = info["bertopic_id"]
            from sqlalchemy.dialects.postgresql import insert
            from app.models.models import Topic as TopicModel
            stmt_t = (
                insert(TopicModel)
                .values(name=info["name"], keywords=info["keywords"])
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={"name": info["name"], "keywords": info["keywords"]},
                )
                .returning(TopicModel.id)
            )
            r = await db.execute(stmt_t)
            db_id = r.scalar_one()
            bertopic_to_db_id[tid] = db_id

        # For fallback keyword topics
        for tid, name in names.items():
            from sqlalchemy.dialects.postgresql import insert
            from app.models.models import Topic as TopicModel
            existing_r = await db.execute(select(TopicModel).where(TopicModel.name == name))
            existing = existing_r.scalar_one_or_none()
            if existing:
                bertopic_to_db_id[tid] = existing.id
            else:
                t = TopicModel(name=name, keywords=[])
                db.add(t)
                await db.flush()
                bertopic_to_db_id[tid] = t.id

        # Insert post_topic rows
        for post_id, btopic_id, confidence in assignments:
            db_topic_id = bertopic_to_db_id.get(btopic_id)
            if db_topic_id:
                db.add(PostTopic(post_id=post_id, topic_id=db_topic_id, confidence=confidence))

        await db.commit()
        return len(assignments)


# ── Trend scoring task ─────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.recompute_trends", bind=True, max_retries=2)
def recompute_trends(self):
    """Recompute composite trend scores from ingested posts."""
    try:
        count = asyncio.run(_recompute_trends_async())
        logger.info("trends_recomputed", count=count)
        return {"status": "ok", "count": count}
    except Exception as exc:
        logger.error("trends_recompute_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


async def _recompute_trends_async() -> int:
    from app.core.database import SessionLocal
    from app.services.trend_engine import recompute_trends as _rt
    async with SessionLocal() as db:
        return await _rt(db)


# ── TTL cleanup task ───────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.cleanup_expired_posts", bind=True, max_retries=2)
def cleanup_expired_posts(self):
    """Delete raw_posts past their 30-day TTL (DPDP Act 2023 compliance)."""
    try:
        count = asyncio.run(_cleanup_expired())
        logger.info("expired_posts_cleaned", count=count)
        return {"status": "ok", "deleted": count}
    except Exception as exc:
        logger.error("cleanup_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=120)


async def _cleanup_expired() -> int:
    from datetime import datetime, timezone
    from sqlalchemy import delete
    from app.core.database import SessionLocal
    from app.models.models import RawPost
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        result = await db.execute(
            delete(RawPost).where(RawPost.expires_at <= now)
        )
        await db.commit()
        return result.rowcount or 0


# ── Segmentation task ─────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.run_segmentation", bind=True, max_retries=2)
def run_segmentation(self):
    """Cluster anonymous author-hashes into demographic segments and generate personas."""
    try:
        count = asyncio.run(_run_segmentation_async())
        logger.info("segmentation_done", count=count)
        return {"status": "ok", "count": count}
    except Exception as exc:
        logger.error("segmentation_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=120)


async def _run_segmentation_async() -> int:
    from app.core.database import SessionLocal
    from app.services.segmentation import run_full_segmentation
    async with SessionLocal() as db:
        return await run_full_segmentation(db)


# ── Legacy stub ────────────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.run_synthetic_ingestion", bind=True, max_retries=3)
def run_synthetic_ingestion(self):
    return run_platform_ingestion.apply()

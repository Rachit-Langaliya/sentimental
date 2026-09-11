from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sih_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Primary ingestion: all platform connectors every 2 minutes
        "ingest-all-platforms": {
            "task": "app.workers.tasks.run_platform_ingestion",
            "schedule": 120.0,
        },
        # Catch-up NLP: process any unanalysed posts every 5 minutes
        "nlp-catch-up": {
            "task": "app.workers.tasks.process_nlp_batch",
            "schedule": 300.0,
            "kwargs": {"limit": 150},
        },
    },
)

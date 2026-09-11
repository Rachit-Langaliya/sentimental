from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class NormalizedPost:
    platform: str
    external_id: str
    author_hash: str
    content: str
    content_cleaned: str
    language: Optional[str]
    geo_hint: Optional[str]
    post_ts: datetime
    parent_hash: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ConnectorStatus:
    platform: str
    mode: str          # "mock" | "live"
    is_healthy: bool
    posts_ingested_total: int = 0
    last_ingested_at: Optional[datetime] = None
    error: Optional[str] = None


class BaseConnector(ABC):
    platform_name: str = ""
    mode: str = "mock"

    @abstractmethod
    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        """Fetch posts from the platform and return normalized records."""
        ...

    async def health_check(self) -> ConnectorStatus:
        try:
            posts = await self.fetch_posts(limit=1)
            return ConnectorStatus(
                platform=self.platform_name,
                mode=self.mode,
                is_healthy=len(posts) > 0,
            )
        except Exception as exc:
            return ConnectorStatus(
                platform=self.platform_name,
                mode=self.mode,
                is_healthy=False,
                error=str(exc),
            )

    async def ingest_batch(self, batch_size: int = 50) -> int:
        """
        Fetch a batch and persist to database using bulk INSERT … ON CONFLICT DO NOTHING.
        Returns the number of newly inserted rows.
        """
        from app.core.database import SessionLocal
        from app.models.models import Platform, RawPost
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert

        posts = await self.fetch_posts(limit=batch_size)
        if not posts:
            return 0

        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        async with SessionLocal() as db:
            plat_r = await db.execute(select(Platform).where(Platform.name == self.platform_name))
            platform = plat_r.scalar_one_or_none()
            if not platform:
                return 0

            rows = [
                {
                    "platform_id": platform.id,
                    "external_id": p.external_id,
                    "author_hash": p.author_hash,
                    "content": p.content,
                    "content_cleaned": p.content_cleaned,
                    "language": p.language,
                    "geo_hint": p.geo_hint,
                    "post_ts": p.post_ts,
                    "parent_hash": p.parent_hash,
                    "metadata_": p.metadata or {},
                    "expires_at": expires_at,
                }
                for p in posts
            ]

            stmt = (
                insert(RawPost)
                .values(rows)
                .on_conflict_do_nothing(constraint="uq_raw_posts_platform_external")
                .returning(RawPost.id)
            )
            result = await db.execute(stmt)
            new_ids = result.fetchall()
            await db.commit()
            return len(new_ids)

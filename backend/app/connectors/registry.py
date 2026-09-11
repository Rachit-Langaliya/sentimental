"""
ConnectorRegistry — manages all platform connectors.
Provides fan-out ingestion, health checks, and per-platform stats.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.connectors.base import BaseConnector, ConnectorStatus
from app.connectors.twitter import TwitterConnector
from app.connectors.telegram import TelegramConnector
from app.connectors.instagram import InstagramConnector
from app.connectors.reddit import RedditConnector
from app.connectors.youtube import YouTubeConnector
from app.connectors.facebook import FacebookConnector

logger = structlog.get_logger()

# Per-platform batch sizes — proportional to real-world volume
_BATCH_SIZES = {
    "twitter":   18,
    "telegram":  12,
    "instagram":  8,
    "reddit":     5,
    "youtube":    5,
    "facebook":   7,
}


class ConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {
            "twitter":   TwitterConnector(),
            "telegram":  TelegramConnector(),
            "instagram": InstagramConnector(),
            "reddit":    RedditConnector(),
            "youtube":   YouTubeConnector(),
            "facebook":  FacebookConnector(),
        }
        self._ingestion_counts: dict[str, int] = {k: 0 for k in self._connectors}
        self._last_ingested: dict[str, Optional[datetime]] = {k: None for k in self._connectors}

    def get(self, platform: str) -> Optional[BaseConnector]:
        return self._connectors.get(platform)

    async def ingest_all(self) -> dict[str, int]:
        """Ingest one batch from every connector. Returns per-platform new-post counts."""
        results: dict[str, int] = {}

        async def _ingest_one(platform: str, connector: BaseConnector) -> tuple[str, int]:
            batch = _BATCH_SIZES.get(platform, 10)
            try:
                count = await connector.ingest_batch(batch_size=batch)
                self._ingestion_counts[platform] = self._ingestion_counts.get(platform, 0) + count
                self._last_ingested[platform] = datetime.now(timezone.utc)
                logger.info("connector_ingested", platform=platform, new_posts=count)
                return platform, count
            except Exception as exc:
                logger.error("connector_ingest_failed", platform=platform, error=str(exc))
                return platform, 0

        tasks = [_ingest_one(p, c) for p, c in self._connectors.items()]
        pairs = await asyncio.gather(*tasks)
        return dict(pairs)

    async def health_check_all(self) -> list[ConnectorStatus]:
        statuses = await asyncio.gather(*[c.health_check() for c in self._connectors.values()])
        for s in statuses:
            s.posts_ingested_total = self._ingestion_counts.get(s.platform, 0)
            s.last_ingested_at = self._last_ingested.get(s.platform)
        return list(statuses)

    async def health_check(self, platform: str) -> Optional[ConnectorStatus]:
        connector = self._connectors.get(platform)
        if not connector:
            return None
        status = await connector.health_check()
        status.posts_ingested_total = self._ingestion_counts.get(platform, 0)
        status.last_ingested_at = self._last_ingested.get(platform)
        return status


# Module-level singleton — imported by tasks and API routes
registry = ConnectorRegistry()

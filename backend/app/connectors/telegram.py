"""
Telegram connector.
Mock mode: generates longer analytical posts from Indian public channels.
Live mode: requires TELEGRAM_API_ID + TELEGRAM_API_HASH (stubbed).
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content
from app.core.config import settings

_CHANNELS = [
    "IndiaNewsBreaking", "KisanAwaaz", "TechPolicyIndia", "EconomicsMirror",
    "HealthcareIndiaUpdates", "EVRevolutionIndia", "PolicyWatchIndia",
    "NorthIndiaVoices", "SouthIndiaConnect", "RuralVoicesNetwork",
]

_FILLER_PREFIXES_HI = [
    "📢 जरूरी जानकारी: ", "🔴 ब्रेकिंग: ", "📊 विश्लेषण: ", "🌾 ", "⚡ अपडेट: ",
]
_FILLER_PREFIXES_EN = [
    "📢 BREAKING: ", "🧵 Analysis — ", "📊 Data thread: ", "🔴 Update: ", "⚡ ",
]


class TelegramConnector(BaseConnector):
    platform_name = "telegram"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        if getattr(settings, "TELEGRAM_API_ID", "") and getattr(settings, "TELEGRAM_API_HASH", ""):
            self.mode = "live"

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # Telegram: longer, add a channel-style prefix, can be 500 chars
            prefix = self._rng.choice(_FILLER_PREFIXES_HI if lang == "hi" else _FILLER_PREFIXES_EN)
            content = f"{prefix}{content}"

            # Sometimes add a forward note
            if self._rng.random() < 0.2:
                content += "\n\n↩️ Forwarded from another channel"

            age = self._rng.randint(60, 14400)
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            channel = self._rng.choice(_CHANNELS)
            channel_id = abs(hash(channel)) % 900000000 + 100000000
            msg_id = self._rng.randint(1000, 999999)
            user_n = self._rng.randint(1, 20000)

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"tg_{channel_id}_{msg_id}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "channel_name": channel,
                    "views": self._rng.randint(200, 80000),
                    "forwards": self._rng.randint(0, 5000),
                    "is_forwarded": self._rng.random() < 0.2,
                    "has_media": self._rng.random() < 0.15,
                },
            ))
        return posts

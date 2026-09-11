"""
Facebook connector.
Mock mode: share-heavy posts, older demographic bias, Hindi/regional language heavy.
Live mode: requires FACEBOOK_PAGE_ACCESS_TOKEN (stubbed).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content

_SHARE_PREFIXES_HI = [
    "शेयर करें — ", "जरूर पढ़ें: ", "सब को बताएं — ", "यह खबर देखें: ",
    "👍 ", "महत्वपूर्ण: ",
]
_SHARE_PREFIXES_EN = [
    "Please share — ", "Must read: ", "Sharing this important update: ",
    "Everyone should know: ", "Spread the word — ", "",
]
_REACTIONS_TYPES = ["like", "love", "haha", "wow", "sad", "angry"]


class FacebookConnector(BaseConnector):
    platform_name = "facebook"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # Facebook: share-style prefix, sometimes paragraph-heavy
            prefix = self._rng.choice(_SHARE_PREFIXES_HI if lang == "hi" else _SHARE_PREFIXES_EN)
            content = f"{prefix}{content}"
            if self._rng.random() < 0.25:
                content += "\n\nआप सब की राय क्या है?" if lang == "hi" else "\n\nShare your thoughts in the comments."

            age = self._rng.randint(600, 172800)  # up to 2 days
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            user_n = self._rng.randint(1, 300000)

            # Facebook post ID numeric
            post_id = self._rng.randint(10**14, 10**15 - 1)

            # Reaction distribution
            reactions = {}
            total_reacts = self._rng.randint(0, 5000)
            remaining = total_reacts
            for r in _REACTIONS_TYPES[:-1]:
                val = self._rng.randint(0, remaining)
                reactions[r] = val
                remaining -= val
            reactions["angry"] = remaining

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"fb_{post_id}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "reactions": reactions,
                    "total_reactions": total_reacts,
                    "shares": self._rng.randint(0, 2000),
                    "comments": self._rng.randint(0, 500),
                    "post_type": self._rng.choices(["status", "photo", "link", "video"], weights=[0.4, 0.3, 0.2, 0.1])[0],
                },
            ))
        return posts

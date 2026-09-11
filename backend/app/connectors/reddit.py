"""
Reddit connector.
Mock mode: post/comment style, English-dominant, analytical tone.
Live mode: requires REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET (stubbed).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content

_SUBREDDITS = [
    "india", "IndiaSpeaks", "indianews", "IndiaInvestments",
    "developersIndia", "bangalore", "mumbai", "Chennai",
    "IndianEngineer", "agricultureIndia", "IndiaPolicy", "IndiaElectric",
]

_POST_PREFIXES = [
    "CMV: ", "Discussion: ", "Analysis — ", "[Serious] ", "Hot take: ",
    "Genuine question: ", "PSA: ", "Long post — ", "", "", "",  # blank = no prefix (most common)
]


class RedditConnector(BaseConnector):
    platform_name = "reddit"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # Reddit: add discussion context, possibly longer
            prefix = self._rng.choice(_POST_PREFIXES)
            content = f"{prefix}{content}"
            if self._rng.random() < 0.3:
                content += f"\n\nCurious what r/{self._rng.choice(_SUBREDDITS)} thinks."

            age = self._rng.randint(600, 259200)  # up to 3 days old
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            user_n = self._rng.randint(1, 200000)
            subreddit = self._rng.choice(_SUBREDDITS)

            # Reddit post ID: base36-style 6-7 chars
            chars = "abcdefghijklmnopqrstuvwxyz0123456789"
            post_id = "".join(self._rng.choices(chars, k=7))

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"rd_{post_id}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "subreddit": subreddit,
                    "score": self._rng.randint(-10, 2500),
                    "upvote_ratio": round(self._rng.uniform(0.5, 0.98), 2),
                    "num_comments": self._rng.randint(0, 400),
                    "post_type": self._rng.choices(["link", "text", "text"], weights=[0.2, 0.4, 0.4])[0],
                    "is_oc": self._rng.random() < 0.6,
                },
            ))
        return posts

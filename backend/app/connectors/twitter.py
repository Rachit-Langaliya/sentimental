"""
Twitter/X connector.
Mock mode: generates short, hashtag-heavy posts in Indian political/news style.
Live mode: requires X_BEARER_TOKEN env var (stubbed — add in production).
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content
from app.core.config import settings

_TWEET_HASHTAG_CLOUDS = {
    "fuel_prices":     ["#FuelPrice", "#PetrolDiesel", "#MahangaiBadh", "#India"],
    "ai_regulation":   ["#AIPolicy", "#TechIndia", "#DigitalIndia", "#AIGovernance"],
    "agriculture_msp": ["#KisanAndolan", "#MSP", "#Farmers", "#AnnData"],
    "ev_policy":       ["#EVIndia", "#CleanEnergy", "#GreenIndia", "#FAME"],
    "education_reform":["#NEP2020", "#Education", "#StudentRights", "#ShikshaNiti"],
    "healthcare":      ["#AyushmanBharat", "#Health", "#PMJAY", "#HealthForAll"],
    "employment":      ["#Jobs", "#Rozgar", "#SkillIndia", "#StartupIndia"],
}


class TwitterConnector(BaseConnector):
    platform_name = "twitter"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        if getattr(settings, "X_BEARER_TOKEN", ""):
            self.mode = "live"

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # Twitter-specific: trim to 280, append 1-2 hashtags
            content = content[:260]
            tags = self._rng.sample(_TWEET_HASHTAG_CLOUDS.get(topic_id, ["#India"]), k=min(2, len(_TWEET_HASHTAG_CLOUDS.get(topic_id, ["#India"]))))
            content = f"{content} {' '.join(tags)}"

            age = self._rng.randint(30, 3600)
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            user_n = self._rng.randint(1, 50000)

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"tw_{self._rng.randint(10**15, 10**16 - 1)}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "like_count": self._rng.randint(0, 8000),
                    "retweet_count": self._rng.randint(0, 3000),
                    "reply_count": self._rng.randint(0, 500),
                    "tweet_type": self._rng.choice(["original", "original", "reply", "quote"]),
                    "verified": self._rng.random() < 0.03,
                },
            ))
        return posts

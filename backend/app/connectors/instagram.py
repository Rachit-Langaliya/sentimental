"""
Instagram connector.
Mock mode: caption-style posts with hashtag clouds, urban Indian context.
Live mode: requires INSTAGRAM_ACCESS_TOKEN (stubbed).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content

_HASHTAG_CLOUDS = [
    "#India #IndianPolitics #Trending #ViralNews #MustWatch",
    "#NewIndia #YoungIndia #DigitalIndia #Bharat #NarendraModi",
    "#EVRevolution #GreenIndia #ClimateAction #SustainableLiving",
    "#FarmersRights #KisanKiAawaz #Agriculture #RuralIndia",
    "#Education #StudentLife #IndianStudents #NEP2020",
    "#HealthForAll #AyushmanBharat #PublicHealth #IndiaHealth",
    "#StartupIndia #Innovation #JobsInIndia #MakeInIndia",
]

_CAPTION_SUFFIXES_EN = [
    "\n\nWhat do you think? Drop your views below 👇",
    "\n\nShare if you agree! 🙏",
    "\n\nSave this for later 📌",
    "\n\nTag someone who needs to see this ☝️",
    "\n\n(Swipe for details →)",
]


class InstagramConnector(BaseConnector):
    platform_name = "instagram"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # Instagram: add hashtag cloud + engagement suffix
            hashtags = self._rng.choice(_HASHTAG_CLOUDS)
            suffix = self._rng.choice(_CAPTION_SUFFIXES_EN) if self._rng.random() < 0.5 else ""
            content = f"{content}{suffix}\n\n{hashtags}"

            age = self._rng.randint(300, 86400)
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            user_n = self._rng.randint(1, 100000)

            # Instagram shortcode-style ID
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
            shortcode = "".join(self._rng.choices(chars, k=11))

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"ig_{shortcode}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "like_count": self._rng.randint(10, 50000),
                    "comment_count": self._rng.randint(0, 2000),
                    "post_type": self._rng.choices(["photo", "reel", "carousel"], weights=[0.4, 0.4, 0.2])[0],
                    "save_count": self._rng.randint(0, 5000),
                },
            ))
        return posts

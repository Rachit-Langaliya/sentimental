"""
YouTube connector.
Mock mode: generates video comment-style content, mixed language.
Live mode: requires YOUTUBE_API_KEY (stubbed).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost
from app.connectors._shared import GEO_HINTS, author_hash, generate_content

_VIDEO_CHANNELS = [
    "DD News", "NDTV India", "ABP News", "Aaj Tak", "Republic Bharat",
    "The Wire", "Firstpost", "Times Now", "India Today", "News18 India",
    "Rajya Sabha TV", "Sansad TV",
]

_COMMENT_PREFIXES_EN = [
    "Great video! ", "This is exactly what I've been saying — ", "Finally someone talking about ",
    "Thanks for covering ", "Important topic: ", "Watched the whole thing. ",
    "Sharing this with everyone. ", "Love this channel. ",
]
_COMMENT_PREFIXES_HI = [
    "बहुत अच्छा वीडियो! ", "बिल्कुल सही बात कही। ", "यह बहुत जरूरी मुद्दा है — ",
    "सभी को देखना चाहिए। ", "धन्यवाद इस जानकारी के लिए। ",
]


class YouTubeConnector(BaseConnector):
    platform_name = "youtube"
    mode = "mock"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        posts = []
        for _ in range(limit):
            content, lang, topic_id = generate_content(self.platform_name, self._rng)

            # YouTube: comment style — usually shorter with a reaction prefix
            prefix = self._rng.choice(_COMMENT_PREFIXES_HI if lang == "hi" else _COMMENT_PREFIXES_EN)
            content = f"{prefix}{content}"

            age = self._rng.randint(60, 604800)  # up to 1 week
            post_ts = datetime.now(timezone.utc) - timedelta(seconds=age)
            user_n = self._rng.randint(1, 500000)
            channel = self._rng.choice(_VIDEO_CHANNELS)

            # YouTube video ID: 11 chars
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
            video_id = "".join(self._rng.choices(chars, k=11))
            comment_id = "".join(self._rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=26))

            posts.append(NormalizedPost(
                platform=self.platform_name,
                external_id=f"yt_{comment_id}",
                author_hash=author_hash(self.platform_name, f"user_{user_n}"),
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=self._rng.choice(GEO_HINTS),
                post_ts=post_ts,
                metadata={
                    "synthetic": True,
                    "topic": topic_id,
                    "video_id": video_id,
                    "channel_name": channel,
                    "like_count": self._rng.randint(0, 10000),
                    "reply_count": self._rng.randint(0, 200),
                    "is_reply": self._rng.random() < 0.35,
                },
            ))
        return posts

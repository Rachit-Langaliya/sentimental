"""
Synthetic data connector — generates realistic Indian social media posts
for demo purposes. Each batch produces varied content across topics.
Phase 2 will add real platform connectors alongside this.
"""
import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.connectors.base import BaseConnector, NormalizedPost

_TOPICS = [
    ("fuel price hike", ["petrol", "diesel", "price", "increase", "tax", "burden"]),
    ("AI regulation", ["artificial intelligence", "AI policy", "tech regulation", "data privacy"]),
    ("agriculture MSP", ["MSP", "kisan", "farmer", "procurement", "crop price"]),
    ("EV policy", ["electric vehicle", "EV", "subsidy", "charging", "green"]),
    ("education reform", ["NEP", "student", "university", "fee", "exam", "scholarship"]),
    ("healthcare", ["hospital", "insurance", "medicine", "ayushman", "health scheme"]),
    ("employment", ["job", "unemployment", "placement", "skill India", "startup"]),
]

_TEMPLATES_EN = [
    "The new {topic} announcement is really concerning for ordinary citizens. #policy",
    "Interesting development on {topic}. What does this mean for us? Thread below 👇",
    "Finally some good news about {topic}! This has been long overdue.",
    "Not sure about the {topic} decision. Too many unanswered questions. #India",
    "Why is nobody talking about the real impact of {topic} on middle-class families?",
    "The {keywords} situation is getting out of hand. Government needs to act NOW.",
    "Actually {topic} is more complex than the headlines suggest. Here's why:",
    "Breaking: New development in {topic} debate. Reactions pouring in. 🔥",
]

_TEMPLATES_HI = [
    "नए {topic} के फैसले से आम आदमी पर बहुत असर पड़ेगा। आपकी राय? #India",
    "{topic} पर सरकार का यह निर्णय बिल्कुल गलत है! #protest",
    "अच्छा लगा {topic} पर कुछ सकारात्मक खबर। उम्मीद है ये जारी रहेगा।",
    "{keywords} का मुद्दा बहुत गंभीर है। इसपर बात होनी चाहिए।",
    "{topic} के बारे में मीडिया पूरी बात नहीं बता रही। सच क्या है?",
]

_TEMPLATES_TA = [
    "{topic} பற்றிய அரசு முடிவு சரியானதா? #TamilNadu",
    "{keywords} நிலைமை மிகவும் கவலையளிக்கிறது.",
    "{topic} குறித்த புதிய செய்திகள் ஆச்சரியமாக உள்ளன।",
]

_GEO_HINTS = [
    "Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad",
    "Lucknow", "Pune", "Kolkata", "Jaipur", "Ahmedabad",
    None, None, None,  # ~30% no geo
]

_PLATFORMS = ["twitter", "telegram", "instagram", "reddit", "youtube", "facebook"]
_PLATFORM_WEIGHTS = [0.35, 0.25, 0.15, 0.10, 0.08, 0.07]
_LANG_WEIGHTS = {"en": 0.55, "hi": 0.28, "ta": 0.10, "te": 0.07}


def _author_hash(seed: str) -> str:
    return hashlib.sha256(f"synthetic-{seed}".encode()).hexdigest()[:16]


def _make_post(platform: str, rng: random.Random) -> NormalizedPost:
    topic_name, keywords = rng.choice(_TOPICS)
    lang = rng.choices(list(_LANG_WEIGHTS.keys()), weights=list(_LANG_WEIGHTS.values()))[0]

    if lang == "en":
        template = rng.choice(_TEMPLATES_EN)
        content = template.format(topic=topic_name, keywords=rng.choice(keywords))
    elif lang == "hi":
        template = rng.choice(_TEMPLATES_HI)
        content = template.format(topic=topic_name, keywords=rng.choice(keywords))
    else:
        template = rng.choice(_TEMPLATES_TA)
        content = template.format(topic=topic_name, keywords=rng.choice(keywords))

    age_seconds = rng.randint(60, 7200)
    post_ts = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)

    author_seed = f"{platform}-user-{rng.randint(1, 10000)}"

    return NormalizedPost(
        platform=platform,
        external_id=str(uuid.uuid4())[:12],
        author_hash=_author_hash(author_seed),
        content=content,
        content_cleaned=content,
        language=lang,
        geo_hint=rng.choice(_GEO_HINTS),
        post_ts=post_ts,
        metadata={"synthetic": True, "topic": topic_name, "demo": True},
    )


class SyntheticConnector(BaseConnector):
    platform_name = "twitter"  # default; override per connector

    def __init__(self, platform: str = "twitter", seed: Optional[int] = None):
        self.platform_name = platform
        self._rng = random.Random(seed)

    async def fetch_posts(self, since: Optional[datetime] = None, limit: int = 100) -> list[NormalizedPost]:
        return [_make_post(self.platform_name, self._rng) for _ in range(limit)]

    async def ingest_batch(self, batch_size: int = 20) -> int:
        total = 0
        for platform in _PLATFORMS:
            self.platform_name = platform
            n = max(1, int(batch_size * _PLATFORM_WEIGHTS[_PLATFORMS.index(platform)]))
            total += await super().ingest_batch(batch_size=n)
        return total

"""
Idempotent seed functions — safe to call on every startup.
Creates platforms, admin user, and demo demographic segments.
"""
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import DemographicSegment, Persona, Platform, Trend, User, UserRole

logger = structlog.get_logger()

_PLATFORMS = [
    {"name": "twitter", "display_name": "X / Twitter", "color": "#1D9BF0", "icon": "twitter"},
    {"name": "telegram", "display_name": "Telegram", "color": "#2AABEE", "icon": "send"},
    {"name": "instagram", "display_name": "Instagram", "color": "#E1306C", "icon": "instagram"},
    {"name": "reddit", "display_name": "Reddit", "color": "#FF4500", "icon": "reddit"},
    {"name": "youtube", "display_name": "YouTube", "color": "#FF0000", "icon": "youtube"},
    {"name": "facebook", "display_name": "Facebook", "color": "#1877F2", "icon": "facebook"},
]

_SEGMENTS = [
    {
        "name": "Urban 18–30 Hindi-speaking",
        "description": "Young urban professionals and students in Hindi-belt states with high social media activity.",
        "dominant_language": "Hindi",
        "geo_distribution": {"Uttar Pradesh": 28, "Maharashtra": 22, "Delhi": 18, "Bihar": 12, "Other": 20},
        "topic_prefs": {"employment": 0.34, "fuel_prices": 0.28, "education": 0.22, "politics": 0.16},
        "sentiment_profile": {"positive": 0.24, "neutral": 0.38, "negative": 0.38},
        "activity_profile": {"19-23h": 0.42, "12-15h": 0.23, "07-10h": 0.18, "other": 0.17},
        "size_estimate": 48200,
        "confidence": 0.81,
        "evidence_count": 8420,
        "persona_summary": (
            "Urban Hindi-speaking youth aged 18–30 show strong engagement with employment, education, and cost-of-living topics. "
            "They tend toward neutral-to-negative sentiment on economic policy, with high reaction intensity on fuel prices and job market discussions. "
            "Active primarily on X and Telegram in evening hours. Cross-platform participation is above average. "
            "This segment amplifies content rapidly within their network and shows sensitivity to any policy perceived as increasing daily expenses."
        ),
        "persona_interests": ["employment news", "startup ecosystem", "cricket", "tech policy", "street food culture"],
        "persona_reaction": {"economic_policy": 0.79, "technology": 0.52, "sports": 0.41, "culture": 0.35},
    },
    {
        "name": "South India Tech Professionals",
        "description": "Technology sector workers in Bengaluru, Chennai, Hyderabad. High English and regional language mix.",
        "dominant_language": "English + Telugu/Tamil/Kannada",
        "geo_distribution": {"Karnataka": 38, "Tamil Nadu": 28, "Telangana": 22, "Kerala": 12},
        "topic_prefs": {"ai_policy": 0.38, "tech_industry": 0.31, "employment": 0.19, "environmental": 0.12},
        "sentiment_profile": {"positive": 0.38, "neutral": 0.42, "negative": 0.20},
        "activity_profile": {"19-23h": 0.38, "07-10h": 0.28, "12-14h": 0.22, "other": 0.12},
        "size_estimate": 31600,
        "confidence": 0.86,
        "evidence_count": 11240,
        "persona_summary": (
            "South Indian technology professionals are highly engaged with AI and digital policy discussions. "
            "Predominantly positive-to-neutral sentiment, with the highest engagement on topics relating to the IT sector, "
            "startup regulation, and digital infrastructure. Multilingual — mix of English with Telugu, Tamil, or Kannada. "
            "React negatively to perceived brain-drain policies or IT sector taxation. Influential in spreading nuanced policy analysis."
        ),
        "persona_interests": ["AI policy", "startup regulation", "digital infrastructure", "cricket IPL", "EV adoption"],
        "persona_reaction": {"tech_policy": 0.82, "economic_policy": 0.58, "employment": 0.71, "environment": 0.49},
    },
    {
        "name": "Rural Agriculture-Connected",
        "description": "Users with strong rural and agriculture connections, primarily in Punjab, Haryana, MP, and UP.",
        "dominant_language": "Hindi + Punjabi",
        "geo_distribution": {"Punjab": 24, "Haryana": 22, "Madhya Pradesh": 20, "Uttar Pradesh": 18, "Other": 16},
        "topic_prefs": {"agriculture_policy": 0.44, "fuel_prices": 0.26, "loan_waivers": 0.18, "weather": 0.12},
        "sentiment_profile": {"positive": 0.19, "neutral": 0.34, "negative": 0.47},
        "activity_profile": {"19-23h": 0.35, "05-08h": 0.28, "12-14h": 0.21, "other": 0.16},
        "size_estimate": 22400,
        "confidence": 0.74,
        "evidence_count": 5870,
        "persona_summary": (
            "Rural and agriculture-connected users show the highest reaction intensity on fuel prices, MSP policy, and farm loan topics. "
            "Predominantly negative sentiment on economic policies perceived as anti-farmer. Active on Telegram groups and WhatsApp-forwarded content. "
            "Content from this segment spreads rapidly through regional-language networks. High community cohesion — "
            "opinions tend to align within the segment. Strong seasonal reactivity around harvest and procurement season."
        ),
        "persona_interests": ["MSP rates", "kisan movements", "monsoon forecasts", "diesel prices", "fertiliser subsidies"],
        "persona_reaction": {"fuel_prices": 0.91, "agriculture_policy": 0.88, "water_policy": 0.72, "education": 0.29},
    },
    {
        "name": "Urban Upper-Middle English Media",
        "description": "English-dominant urban users following mainstream English news media. Diverse professional backgrounds.",
        "dominant_language": "English",
        "geo_distribution": {"Mumbai": 28, "Delhi": 26, "Bengaluru": 18, "Chennai": 12, "Other": 16},
        "topic_prefs": {"fiscal_policy": 0.31, "geopolitics": 0.26, "tech_policy": 0.22, "environment": 0.21},
        "sentiment_profile": {"positive": 0.29, "neutral": 0.48, "negative": 0.23},
        "activity_profile": {"07-10h": 0.31, "12-14h": 0.26, "19-22h": 0.28, "other": 0.15},
        "size_estimate": 19800,
        "confidence": 0.83,
        "evidence_count": 9100,
        "persona_summary": (
            "English-speaking urban professionals show measured, analytical engagement with policy topics. "
            "Lower reaction intensity but higher influence on mainstream discourse. "
            "Balanced sentiment distribution — highest neutral proportion of any segment, reflecting analytical engagement style. "
            "Active on X and LinkedIn. Tends to set agenda for media coverage rather than follow it. "
            "Responsive to international comparison narratives and GDP/fiscal metric framing."
        ),
        "persona_interests": ["fiscal policy", "geopolitics", "climate change", "equity markets", "urban infrastructure"],
        "persona_reaction": {"economic_policy": 0.67, "tech_policy": 0.71, "geopolitics": 0.64, "social_policy": 0.58},
    },
]

_TRENDS = [
    {"name": "Fuel price hike debate", "trend_score": 0.847, "velocity": 0.62, "acceleration": 0.18, "is_emerging": True, "platform_count": 4, "unique_users": 8420, "platforms": ["twitter", "telegram", "reddit", "youtube"]},
    {"name": "AI regulation policy", "trend_score": 0.731, "velocity": 0.44, "acceleration": 0.09, "is_emerging": True, "platform_count": 3, "unique_users": 6210, "platforms": ["twitter", "reddit", "youtube"]},
    {"name": "Agriculture MSP reform", "trend_score": 0.682, "velocity": 0.38, "acceleration": 0.04, "is_emerging": False, "platform_count": 3, "unique_users": 4890, "platforms": ["twitter", "telegram", "facebook"]},
    {"name": "EV subsidy expansion", "trend_score": 0.614, "velocity": 0.28, "acceleration": 0.11, "is_emerging": True, "platform_count": 3, "unique_users": 3760, "platforms": ["twitter", "youtube", "reddit"]},
    {"name": "Urban infrastructure spend", "trend_score": 0.571, "velocity": 0.19, "acceleration": -0.02, "is_emerging": False, "platform_count": 2, "unique_users": 2940, "platforms": ["twitter", "telegram"]},
    {"name": "Education loan policy", "trend_score": 0.523, "velocity": 0.31, "acceleration": 0.06, "is_emerging": False, "platform_count": 4, "unique_users": 5100, "platforms": ["twitter", "telegram", "reddit", "youtube"]},
    {"name": "Healthcare digitisation", "trend_score": 0.489, "velocity": 0.14, "acceleration": 0.02, "is_emerging": False, "platform_count": 2, "unique_users": 2210, "platforms": ["twitter", "facebook"]},
]


async def seed_platforms() -> None:
    async with SessionLocal() as db:
        for p in _PLATFORMS:
            existing = await db.execute(select(Platform).where(Platform.name == p["name"]))
            if existing.scalar_one_or_none():
                continue
            db.add(Platform(**p))
        await db.commit()
    logger.info("seed_platforms_done")


async def seed_admin_user() -> None:
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if existing.scalar_one_or_none():
            return
        admin = User(
            email=settings.ADMIN_EMAIL,
            full_name=settings.ADMIN_NAME,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
    logger.info("seed_admin_done", email=settings.ADMIN_EMAIL)

    # Seed demo data only once
    await seed_demo_data()


async def seed_demo_data() -> None:
    """Seed realistic demo segments, personas, and trends."""
    async with SessionLocal() as db:
        existing = await db.execute(select(DemographicSegment))
        if existing.scalars().first():
            return  # already seeded

        now = datetime.now(timezone.utc)

        for seg_data in _SEGMENTS:
            persona_summary = seg_data.pop("persona_summary")
            persona_interests = seg_data.pop("persona_interests")
            persona_reaction = seg_data.pop("persona_reaction")

            seg = DemographicSegment(**seg_data, updated_at=now)
            db.add(seg)
            await db.flush()  # get id

            persona = Persona(
                segment_id=seg.id,
                summary=persona_summary,
                interests=persona_interests,
                reaction=persona_reaction,
                influence_score=round(seg_data["confidence"] * 0.9, 2),
                confidence=seg_data["confidence"],
                evidence_json={"source": "synthetic_demo", "method": "behavioral_clustering"},
                generated_at=now,
            )
            db.add(persona)

        for trend_data in _TRENDS:
            db.add(Trend(**trend_data, measured_at=now, volume_decay=0.3, engagement=0.6, community_spread=0.5, sentiment_shift=0.08, baseline_7d=0.2))

        await db.commit()
    logger.info("seed_demo_data_done", segments=len(_SEGMENTS), trends=len(_TRENDS))

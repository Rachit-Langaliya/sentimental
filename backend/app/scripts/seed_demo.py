"""
Demo data seeder — Phase 7.

Populates the database with ~2 000 realistic posts, NLP results, topics,
trends, segments, and personas so the platform shows meaningful data the
moment it starts.  Safe to run multiple times (idempotent via upserts /
existence checks).

Usage:
    python -m app.scripts.seed_demo          # from backend/
    docker compose --profile seed up seeder  # via Docker
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import (
    AuditLog,
    DemographicSegment,
    Persona,
    Platform,
    PostNLP,
    PostTopic,
    RawPost,
    Topic,
    Trend,
    User,
    UserRole,
)

# ── RNG seed for deterministic output ────────────────────────────────────────

RNG = random.Random(2026)

# ── Content templates per topic × language ────────────────────────────────────

_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "fuel_prices": {
        "en": [
            "Petrol prices up again — when will it stop?",
            "Fuel hike is killing small businesses and daily commuters.",
            "Diesel prices at record high. Government must intervene.",
            "Every week a new fuel price increase. Middle class is suffering.",
            "LPG cylinder cost has doubled in two years. Unacceptable.",
            "Rising fuel costs are driving up the price of everything.",
            "Petrol at ₹105/litre in my city. Completely unsustainable.",
        ],
        "hi": [
            "पेट्रोल की कीमतें फिर बढ़ीं, आम आदमी कहाँ जाए?",
            "डीजल इतना महंगा हो गया है कि ट्रकिंग कारोबार चौपट हो रहा है।",
            "एलपीजी सिलेंडर ₹900 पार — सरकार कब जागेगी?",
            "ईंधन की बढ़ती कीमतें महंगाई की असली वजह हैं।",
            "पेट्रोल-डीजल पर टैक्स कम करो, जनता राहत चाहती है।",
        ],
        "ta": [
            "பெட்ரோல் விலை மீண்டும் உயர்ந்தது — மக்கள் கஷ்டப்படுகிறார்கள்.",
            "இந்த விலை உயர்வை அரசு கட்டுப்படுத்தணும்.",
        ],
    },
    "agriculture_msp": {
        "en": [
            "Government increases MSP for wheat — good news for farmers.",
            "Kisan credit card scheme helping rural households.",
            "PM-KISAN transfer received. Thank you government.",
            "Farmer protests easing as MSP guarantee bill progresses.",
            "Crop insurance scheme coverage expanded to more districts.",
            "Direct benefit transfers reaching farmers faster now.",
        ],
        "hi": [
            "एमएसपी बढ़ोतरी से किसानों को राहत मिलेगी।",
            "पीएम किसान योजना का पैसा खाते में आ गया।",
            "फसल बीमा योजना में सुधार का स्वागत है।",
            "किसान क्रेडिट कार्ड से खेती में मदद मिल रही है।",
            "सरकारी खरीद केंद्र गांव के पास खुले, सुविधा हुई।",
        ],
        "te": [
            "వ్యవసాయదారులకు MSP పెంచడం మంచి నిర్ణయం.",
            "కిసాన్ పథకం ద్వారా రైతులకు ప్రత్యక్ష సహాయం.",
        ],
    },
    "ev_adoption": {
        "en": [
            "EV subsidies announced — great step towards clean transport.",
            "Charging infrastructure needs massive expansion in tier-2 cities.",
            "Electric scooter sales up 300% this year. India going green!",
            "Government PLI scheme boosting domestic EV manufacturing.",
            "Battery swapping stations rollout will accelerate EV adoption.",
            "Electric buses in city transport reducing pollution significantly.",
            "EV loan interest subsidy makes it more affordable now.",
        ],
        "hi": [
            "इलेक्ट्रिक वाहन सब्सिडी से बाजार में तेजी आएगी।",
            "चार्जिंग स्टेशनों की संख्या बढ़ानी होगी।",
            "ई-बस से शहरों की हवा साफ होगी।",
        ],
    },
    "education": {
        "en": [
            "NEP 2020 implementation bringing multilingual learning.",
            "Digital classroom scheme reaching remote villages.",
            "School dropout rate falling under new education reforms.",
            "Scholarship scheme helping first-generation college students.",
            "STEM labs in government schools — positive change.",
            "Mid-day meal improvement helping attendance rates.",
        ],
        "hi": [
            "नई शिक्षा नीति से बच्चों को मातृभाषा में पढ़ाई का मौका मिलेगा।",
            "डिजिटल शिक्षा दूरदराज के गांवों तक पहुँच रही है।",
            "छात्रवृत्ति योजना से गरीब परिवारों के बच्चों को फायदा।",
            "सरकारी स्कूलों में बुनियादी ढांचे में सुधार जरूरी है।",
        ],
        "bn": [
            "নতুন শিক্ষানীতিতে মাতৃভাষায় পড়াশোনার সুযোগ।",
            "ডিজিটাল শ্রেণীকক্ষ প্রকল্প গ্রামে পৌঁছাচ্ছে।",
        ],
    },
    "healthcare": {
        "en": [
            "Ayushman Bharat coverage extended to 10 crore more families.",
            "Jan Aushadhi stores providing medicines at affordable prices.",
            "Mental health helpline usage increasing — awareness growing.",
            "New AIIMS in tier-2 cities will reduce medical travel burden.",
            "Vaccination drive successful — polio-free India milestone.",
            "Generic medicines policy saving patients thousands annually.",
        ],
        "hi": [
            "आयुष्मान भारत योजना से गरीबों को इलाज मिल रहा है।",
            "जन औषधि केंद्र से सस्ती दवाएं मिल रही हैं।",
            "नए एम्स से इलाज के लिए दूर नहीं जाना पड़ेगा।",
        ],
        "ta": [
            "ஆயுஷ்மான் பாரத் திட்டம் ஏழை மக்களுக்கு உதவுகிறது.",
        ],
    },
    "taxation_gst": {
        "en": [
            "GST on essential food items needs to be reduced immediately.",
            "Middle class is overtaxed while large corporations get exemptions.",
            "Income tax threshold should be raised to ₹10 lakh.",
            "GST compliance burden on small businesses is too high.",
            "Tax reform needed — simplify the slab structure.",
        ],
        "hi": [
            "जीएसटी दरें जरूरी चीजों पर कम होनी चाहिए।",
            "मध्यम वर्ग पर टैक्स का बोझ बहुत ज्यादा है।",
            "इनकम टैक्स छूट सीमा बढ़ाई जाए।",
        ],
    },
    "infrastructure": {
        "en": [
            "New expressway cutting travel time between cities by half.",
            "Railway electrification project on schedule across all zones.",
            "Smart city mission improving urban infrastructure quality.",
            "Metro expansion bringing relief to commuters in large cities.",
            "Optical fibre reaching gram panchayats under BharatNet.",
        ],
        "hi": [
            "नया एक्सप्रेसवे यात्रा समय आधा कर देगा।",
            "रेलवे विद्युतीकरण से प्रदूषण कम होगा।",
            "स्मार्ट सिटी परियोजना से शहर बदल रहे हैं।",
            "भारतनेट से गाँवों में इंटरनेट पहुँचा।",
        ],
    },
    "environment": {
        "en": [
            "Delhi AQI crossed 400 again. Emergency health alert issued.",
            "Forest fires increasing due to climate change. Need action.",
            "Solar capacity target achieved ahead of schedule. Great news.",
            "Plastic ban enforcement improving coastal cleanliness.",
            "River rejuvenation project showing positive results.",
        ],
        "hi": [
            "दिल्ली की हवा खतरनाक स्तर पर, प्रदूषण नियंत्रण जरूरी।",
            "सौर ऊर्जा का लक्ष्य समय से पहले हासिल — शानदार।",
            "प्लास्टिक प्रतिबंध से समुद्र तट साफ हो रहे हैं।",
        ],
    },
    "ai_technology": {
        "en": [
            "AI-powered crop advisory helping farmers make better decisions.",
            "Government deploying AI for faster document verification.",
            "India's AI startup ecosystem growing rapidly.",
            "AI in healthcare diagnostics could revolutionise rural care.",
            "Digital India 2.0 integrating AI across governance.",
            "Concerned about AI job displacement in IT sector.",
        ],
        "hi": [
            "एआई से सरकारी सेवाएं तेज़ और पारदर्शी होंगी।",
            "किसानों के लिए एआई आधारित सलाह उपयोगी है।",
        ],
    },
    "social_welfare": {
        "en": [
            "PM housing scheme: 3 crore houses under construction.",
            "Women self-help groups empowered through microfinance.",
            "Free ration scheme extended — relief for poor families.",
            "MGNREGA wages increased to support rural livelihoods.",
            "Skill India programme helping youth find employment.",
        ],
        "hi": [
            "पीएम आवास योजना से गरीब परिवारों को घर मिल रहा है।",
            "मनरेगा मजदूरी बढ़ाने से ग्रामीण आय बढ़ेगी।",
            "मुफ्त राशन योजना से जरूरतमंद परिवारों को राहत।",
        ],
    },
}

# Geo hints by language
_GEO: dict[str, list[str]] = {
    "en": ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata"],
    "hi": ["Delhi", "Lucknow", "Jaipur", "Bhopal", "Patna", "Varanasi", "Indore"],
    "ta": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "te": ["Hyderabad", "Vijayawada", "Visakhapatnam", "Warangal"],
    "bn": ["Kolkata", "Durgapur", "Siliguri"],
    "mr": ["Mumbai", "Pune", "Nagpur", "Nashik"],
}

# Platform distribution weights  [twitter, reddit, facebook, instagram, youtube, news]
_PLATFORM_WEIGHTS = [0.30, 0.15, 0.25, 0.15, 0.10, 0.05]

# Topic distribution weights (mirrors real-world engagement patterns)
_TOPIC_WEIGHTS = {
    "fuel_prices": 0.18,
    "agriculture_msp": 0.14,
    "ev_adoption": 0.10,
    "education": 0.12,
    "healthcare": 0.12,
    "taxation_gst": 0.08,
    "infrastructure": 0.10,
    "environment": 0.07,
    "ai_technology": 0.05,
    "social_welfare": 0.04,
}

# Sentiment bias per topic (positive bias = overall positive)
_SENTIMENT_BIAS: dict[str, float] = {
    "fuel_prices": -0.30,
    "agriculture_msp": +0.20,
    "ev_adoption": +0.25,
    "education": +0.15,
    "healthcare": +0.18,
    "taxation_gst": -0.20,
    "infrastructure": +0.22,
    "environment": -0.15,
    "ai_technology": +0.10,
    "social_welfare": +0.25,
}

# Language distribution per platform
_PLATFORM_LANG_WEIGHTS: dict[str, dict[str, float]] = {
    "twitter":   {"en": 0.40, "hi": 0.35, "ta": 0.10, "te": 0.08, "bn": 0.05, "mr": 0.02},
    "reddit":    {"en": 0.70, "hi": 0.20, "ta": 0.04, "te": 0.03, "bn": 0.02, "mr": 0.01},
    "facebook":  {"en": 0.25, "hi": 0.45, "ta": 0.12, "te": 0.08, "bn": 0.07, "mr": 0.03},
    "instagram": {"en": 0.35, "hi": 0.40, "ta": 0.10, "te": 0.06, "bn": 0.06, "mr": 0.03},
    "youtube":   {"en": 0.40, "hi": 0.38, "ta": 0.08, "te": 0.07, "bn": 0.05, "mr": 0.02},
    "news":      {"en": 0.55, "hi": 0.30, "ta": 0.07, "te": 0.04, "bn": 0.03, "mr": 0.01},
}


def _pick(d: dict[str, float]) -> str:
    keys = list(d.keys())
    weights = [d[k] for k in keys]
    return RNG.choices(keys, weights=weights, k=1)[0]


def _sentiment(topic: str) -> tuple[str, float]:
    bias = _SENTIMENT_BIAS.get(topic, 0.0)
    base_pos = 0.33 + bias * 0.6
    base_neg = 0.33 - bias * 0.4
    base_neu = max(0.05, 1.0 - base_pos - base_neg)
    total = base_pos + base_neg + base_neu
    p, neg, n = base_pos / total, base_neg / total, base_neu / total

    s = RNG.choices(["positive", "negative", "neutral"], weights=[p, neg, n], k=1)[0]
    score = {
        "positive": RNG.uniform(0.55, 0.95),
        "negative": RNG.uniform(0.55, 0.92),
        "neutral":  RNG.uniform(0.48, 0.72),
    }[s]
    return s, round(score, 3)


def _author_hash(platform: str, uid: int) -> str:
    salt = "demo-salt-2026"
    return hashlib.sha256(f"{salt}{platform}{uid}".encode()).hexdigest()[:32]


# ── Platform specs ─────────────────────────────────────────────────────────────

_PLATFORM_SPECS = [
    {"name": "twitter",   "display_name": "X / Twitter",  "color": "#1DA1F2"},
    {"name": "reddit",    "display_name": "Reddit",       "color": "#FF4500"},
    {"name": "facebook",  "display_name": "Facebook",     "color": "#1877F2"},
    {"name": "instagram", "display_name": "Instagram",    "color": "#E1306C"},
    {"name": "youtube",   "display_name": "YouTube",      "color": "#FF0000"},
    {"name": "news",      "display_name": "News Sites",   "color": "#6B7280"},
]

# ── Segment specs ──────────────────────────────────────────────────────────────

_SEGMENT_SPECS = [
    {
        "name": "Hindi-speaking Twitter users interested in Fuel & Energy Prices",
        "description": "Urban and semi-urban Hindi speakers on Twitter expressing strong opinions about fuel price hikes and their impact on daily life.",
        "dominant_language": "Hindi",
        "size_estimate": 4200,
        "confidence": 0.81,
        "topic_prefs": {"fuel_prices": 0.42, "taxation_gst": 0.28, "infrastructure": 0.15, "social_welfare": 0.15},
        "sentiment_profile": {"positive": 0.18, "neutral": 0.32, "negative": 0.50},
        "activity_profile": {"morning": 0.22, "afternoon": 0.28, "evening": 0.35, "night": 0.15},
        "geo_distribution": {"Delhi": 0.30, "UP": 0.22, "Bihar": 0.15, "MP": 0.12, "Rajasthan": 0.11, "Other": 0.10},
        "interests": ["fuel prices", "LPG cost", "inflation", "GST reform"],
        "summary": "This segment represents strongly negative voices primarily discussing fuel & energy price hikes. They are highly vocal on Twitter and respond quickly to government announcements about petrol/diesel pricing.",
        "reaction": {"support_policy": 0.18, "oppose_policy": 0.60, "neutral": 0.22},
    },
    {
        "name": "English-speaking Reddit users interested in AI & Technology",
        "description": "Educated urban professionals engaging in nuanced debate about AI, digital governance, and technology policy on Reddit.",
        "dominant_language": "English",
        "size_estimate": 2800,
        "confidence": 0.87,
        "topic_prefs": {"ai_technology": 0.45, "infrastructure": 0.25, "education": 0.20, "ev_adoption": 0.10},
        "sentiment_profile": {"positive": 0.45, "neutral": 0.38, "negative": 0.17},
        "activity_profile": {"morning": 0.18, "afternoon": 0.32, "evening": 0.38, "night": 0.12},
        "geo_distribution": {"Bangalore": 0.28, "Hyderabad": 0.22, "Mumbai": 0.20, "Delhi": 0.15, "Pune": 0.10, "Other": 0.05},
        "interests": ["AI governance", "digital India", "EV technology", "startup ecosystem"],
        "summary": "This segment represents mostly positive voices discussing AI, technology policy, and digital infrastructure. They tend to be analytical and engage with detailed policy documents.",
        "reaction": {"support_policy": 0.52, "oppose_policy": 0.18, "neutral": 0.30},
    },
    {
        "name": "Tamil-speaking Facebook users interested in Agriculture",
        "description": "Rural and semi-rural Tamil speakers on Facebook discussing agricultural MSP, crop insurance, and farmer welfare schemes.",
        "dominant_language": "Tamil",
        "size_estimate": 3100,
        "confidence": 0.76,
        "topic_prefs": {"agriculture_msp": 0.50, "social_welfare": 0.25, "environment": 0.15, "healthcare": 0.10},
        "sentiment_profile": {"positive": 0.38, "neutral": 0.35, "negative": 0.27},
        "activity_profile": {"morning": 0.30, "afternoon": 0.25, "evening": 0.30, "night": 0.15},
        "geo_distribution": {"Tamil Nadu (Rural)": 0.55, "Tamil Nadu (Urban)": 0.30, "Pondicherry": 0.10, "Other": 0.05},
        "interests": ["MSP policy", "crop insurance", "kisan credit", "farmer protests"],
        "summary": "This segment represents moderately positive voices primarily discussing agricultural policy and farmer welfare. They respond strongly to MSP announcements and crop insurance changes.",
        "reaction": {"support_policy": 0.42, "oppose_policy": 0.30, "neutral": 0.28},
    },
    {
        "name": "English-speaking YouTube users interested in EV Adoption",
        "description": "Tech-savvy urban consumers discussing electric vehicle policy, subsidies, and charging infrastructure on YouTube.",
        "dominant_language": "English",
        "size_estimate": 1900,
        "confidence": 0.83,
        "topic_prefs": {"ev_adoption": 0.55, "environment": 0.25, "infrastructure": 0.12, "ai_technology": 0.08},
        "sentiment_profile": {"positive": 0.58, "neutral": 0.30, "negative": 0.12},
        "activity_profile": {"morning": 0.15, "afternoon": 0.25, "evening": 0.45, "night": 0.15},
        "geo_distribution": {"Bangalore": 0.25, "Delhi": 0.22, "Mumbai": 0.20, "Pune": 0.18, "Chennai": 0.10, "Other": 0.05},
        "interests": ["electric vehicles", "charging infrastructure", "battery tech", "clean transport"],
        "summary": "This segment represents strongly positive voices primarily discussing EV adoption and clean transport policy. They are early adopters and technology enthusiasts who respond very positively to EV subsidies.",
        "reaction": {"support_policy": 0.65, "oppose_policy": 0.10, "neutral": 0.25},
    },
    {
        "name": "Hindi-speaking Instagram users interested in Education",
        "description": "Young students and parents on Instagram discussing NEP 2020, digital education, and scholarship schemes.",
        "dominant_language": "Hindi",
        "size_estimate": 3600,
        "confidence": 0.79,
        "topic_prefs": {"education": 0.55, "social_welfare": 0.20, "ai_technology": 0.15, "healthcare": 0.10},
        "sentiment_profile": {"positive": 0.42, "neutral": 0.38, "negative": 0.20},
        "activity_profile": {"morning": 0.20, "afternoon": 0.15, "evening": 0.40, "night": 0.25},
        "geo_distribution": {"UP": 0.28, "Bihar": 0.18, "MP": 0.15, "Rajasthan": 0.15, "Delhi": 0.12, "Other": 0.12},
        "interests": ["NEP 2020", "scholarships", "digital education", "skill development"],
        "summary": "This segment represents mixed-to-positive voices primarily discussing education policy and youth welfare. They are highly aspirational and respond well to scholarship and skill development announcements.",
        "reaction": {"support_policy": 0.48, "oppose_policy": 0.22, "neutral": 0.30},
    },
    {
        "name": "Telugu-speaking Facebook users interested in Healthcare",
        "description": "Telugu-speaking citizens on Facebook discussing Ayushman Bharat, Jan Aushadhi, and public health infrastructure.",
        "dominant_language": "Telugu",
        "size_estimate": 2200,
        "confidence": 0.74,
        "topic_prefs": {"healthcare": 0.55, "social_welfare": 0.25, "agriculture_msp": 0.12, "education": 0.08},
        "sentiment_profile": {"positive": 0.40, "neutral": 0.35, "negative": 0.25},
        "activity_profile": {"morning": 0.28, "afternoon": 0.22, "evening": 0.35, "night": 0.15},
        "geo_distribution": {"Andhra Pradesh": 0.45, "Telangana": 0.42, "Other": 0.13},
        "interests": ["Ayushman Bharat", "affordable medicines", "rural healthcare", "AIIMS expansion"],
        "summary": "This segment represents moderately positive voices primarily discussing healthcare access and affordability. They strongly support policies that reduce out-of-pocket medical expenses.",
        "reaction": {"support_policy": 0.45, "oppose_policy": 0.25, "neutral": 0.30},
    },
]

# ── Trend specs ────────────────────────────────────────────────────────────────

_TREND_SPECS = [
    {"name": "Petrol Price Hike Backlash", "topic": "fuel_prices", "trend_score": 0.912, "velocity": 4.2, "acceleration": 0.8, "unique_users": 18400, "platform_count": 5, "is_emerging": False, "platforms": ["twitter", "facebook", "reddit", "youtube", "news"], "sentiment_shift": -0.18, "baseline_7d": 3200.0, "community_spread": 0.82},
    {"name": "EV Subsidy Announcement Buzz", "topic": "ev_adoption", "trend_score": 0.874, "velocity": 6.8, "acceleration": 2.1, "unique_users": 9200, "platform_count": 4, "is_emerging": True, "platforms": ["twitter", "reddit", "youtube", "instagram"], "sentiment_shift": 0.31, "baseline_7d": 1100.0, "community_spread": 0.68},
    {"name": "MSP Guarantee Bill Discussion", "topic": "agriculture_msp", "trend_score": 0.821, "velocity": 2.9, "acceleration": 0.4, "unique_users": 14100, "platform_count": 4, "is_emerging": False, "platforms": ["twitter", "facebook", "youtube", "news"], "sentiment_shift": 0.22, "baseline_7d": 2800.0, "community_spread": 0.75},
    {"name": "NEP 2020 Implementation Update", "topic": "education", "trend_score": 0.763, "velocity": 1.8, "acceleration": 0.2, "unique_users": 11200, "platform_count": 4, "is_emerging": False, "platforms": ["twitter", "facebook", "instagram", "youtube"], "sentiment_shift": 0.15, "baseline_7d": 1900.0, "community_spread": 0.61},
    {"name": "Delhi AQI Emergency Alert", "topic": "environment", "trend_score": 0.748, "velocity": 5.3, "acceleration": 1.9, "unique_users": 16800, "platform_count": 5, "is_emerging": True, "platforms": ["twitter", "facebook", "reddit", "instagram", "news"], "sentiment_shift": -0.28, "baseline_7d": 1400.0, "community_spread": 0.79},
    {"name": "Ayushman Bharat Expansion", "topic": "healthcare", "trend_score": 0.692, "velocity": 1.2, "acceleration": 0.1, "unique_users": 8900, "platform_count": 3, "is_emerging": False, "platforms": ["twitter", "facebook", "news"], "sentiment_shift": 0.19, "baseline_7d": 1600.0, "community_spread": 0.55},
    {"name": "GST on Essentials Debate", "topic": "taxation_gst", "trend_score": 0.671, "velocity": 3.1, "acceleration": 0.7, "unique_users": 7400, "platform_count": 3, "is_emerging": False, "platforms": ["twitter", "reddit", "facebook"], "sentiment_shift": -0.14, "baseline_7d": 1200.0, "community_spread": 0.58},
    {"name": "AI in Governance Initiative", "topic": "ai_technology", "trend_score": 0.634, "velocity": 4.5, "acceleration": 1.4, "unique_users": 5800, "platform_count": 3, "is_emerging": True, "platforms": ["twitter", "reddit", "youtube"], "sentiment_shift": 0.12, "baseline_7d": 600.0, "community_spread": 0.44},
    {"name": "New Expressway Network Launch", "topic": "infrastructure", "trend_score": 0.598, "velocity": 1.5, "acceleration": 0.3, "unique_users": 6200, "platform_count": 3, "is_emerging": False, "platforms": ["twitter", "facebook", "news"], "sentiment_shift": 0.20, "baseline_7d": 1100.0, "community_spread": 0.49},
    {"name": "PM Housing Scheme Milestone", "topic": "social_welfare", "trend_score": 0.561, "velocity": 0.9, "acceleration": 0.0, "unique_users": 5100, "platform_count": 3, "is_emerging": False, "platforms": ["twitter", "facebook", "news"], "sentiment_shift": 0.25, "baseline_7d": 900.0, "community_spread": 0.43},
]


# ── Main seeder ────────────────────────────────────────────────────────────────

async def seed(db_url: str) -> None:
    # Use asyncpg driver
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        print("=== SIH Demo Seeder ===")

        platform_ids = await _seed_platforms(db)
        topic_ids = await _seed_topics(db)
        post_ids, post_topic_map = await _seed_posts(db, platform_ids, topic_ids)
        await _seed_nlp(db, post_ids, post_topic_map)
        await _seed_post_topics(db, post_ids, post_topic_map, topic_ids)
        await _seed_trends(db, topic_ids)
        await _seed_segments(db)

        print("\n✓ Demo seeding complete!")
        total = len(post_ids)
        print(f"  Posts: {total}  |  Topics: {len(topic_ids)}  |  Trends: {len(_TREND_SPECS)}  |  Segments: {len(_SEGMENT_SPECS)}")

    await engine.dispose()


async def _seed_platforms(db: AsyncSession) -> dict[str, int]:
    print("\n[1/6] Platforms...")
    result = {}
    for spec in _PLATFORM_SPECS:
        existing = await db.execute(select(Platform).where(Platform.name == spec["name"]))
        p = existing.scalar_one_or_none()
        if p is None:
            p = Platform(
                name=spec["name"],
                display_name=spec["display_name"],
                color=spec["color"],
            )
            db.add(p)
            await db.flush()
            print(f"  + {spec['display_name']}")
        else:
            print(f"  = {spec['display_name']} (exists)")
        result[spec["name"]] = p.id
    await db.commit()
    return result


async def _seed_topics(db: AsyncSession) -> dict[str, int]:
    print("\n[2/6] Topics...")
    result = {}
    for topic_name in _TOPIC_WEIGHTS:
        existing = await db.execute(select(Topic).where(Topic.name == topic_name))
        t = existing.scalar_one_or_none()
        if t is None:
            kws = list(_TEMPLATES.get(topic_name, {}).get("en", [""])[:3])
            t = Topic(
                name=topic_name,
                keywords={"terms": kws},
                first_seen=datetime.now(timezone.utc) - timedelta(days=30),
                platform_ids=[1, 2, 3, 4, 5, 6],
            )
            db.add(t)
            await db.flush()
            print(f"  + {topic_name}")
        else:
            print(f"  = {topic_name} (exists)")
        result[topic_name] = t.id
    await db.commit()
    return result


async def _seed_posts(
    db: AsyncSession,
    platform_ids: dict[str, int],
    topic_ids: dict[str, int],
) -> tuple[list[int], dict[int, str]]:
    print("\n[3/6] Posts (~2000)...")

    # Check existing count
    existing_count_r = await db.execute(text("SELECT COUNT(*) FROM raw_posts"))
    existing = existing_count_r.scalar() or 0
    if existing >= 1500:
        print(f"  = {existing} posts already exist, skipping post creation")
        all_ids_r = await db.execute(text("SELECT id FROM raw_posts ORDER BY id"))
        all_ids = [row[0] for row in all_ids_r.fetchall()]
        # Build a fake post_topic_map from existing posts
        post_topic_map: dict[int, str] = {}
        topic_names = list(topic_ids.keys())
        for i, pid in enumerate(all_ids):
            topic_name = RNG.choices(topic_names, weights=list(_TOPIC_WEIGHTS.values()), k=1)[0]
            post_topic_map[pid] = topic_name
        return all_ids, post_topic_map

    platform_names = list(platform_ids.keys())
    now = datetime.now(timezone.utc)
    topic_names = list(_TOPIC_WEIGHTS.keys())
    topic_wts = list(_TOPIC_WEIGHTS.values())

    TOTAL = 2000
    batch_size = 200
    all_ids: list[int] = []
    post_topic_map: dict[int, str] = {}

    for batch_start in range(0, TOTAL, batch_size):
        batch: list[RawPost] = []
        for _ in range(min(batch_size, TOTAL - batch_start)):
            platform_name = RNG.choices(platform_names, weights=_PLATFORM_WEIGHTS, k=1)[0]
            platform_id = platform_ids[platform_name]
            topic_name = RNG.choices(topic_names, weights=topic_wts, k=1)[0]

            lang_weights = _PLATFORM_LANG_WEIGHTS[platform_name]
            lang = _pick(lang_weights)

            templates = _TEMPLATES.get(topic_name, {}).get(lang, None)
            if not templates:
                lang = "en"
                templates = _TEMPLATES.get(topic_name, {}).get("en", ["No content"])

            content = RNG.choice(templates)
            # Add slight variation
            if RNG.random() < 0.3:
                suffixes = [" 🙏", " thoughts?", " #India", " share your views", " RT if you agree", ""]
                content += RNG.choice(suffixes)

            uid = RNG.randint(1, 800)
            author_hash = _author_hash(platform_name, uid)

            days_ago = RNG.uniform(0, 7)
            hours_jitter = RNG.uniform(-6, 6)
            post_ts = now - timedelta(days=days_ago, hours=hours_jitter)
            post_ts = min(post_ts, now)

            geo = RNG.choice(_GEO.get(lang, ["India"]))
            ext_id = f"demo_{platform_name}_{batch_start + _}_{RNG.randint(10000,99999)}"

            p = RawPost(
                platform_id=platform_id,
                external_id=ext_id,
                author_hash=author_hash,
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=geo,
                post_ts=post_ts,
                expires_at=now + timedelta(days=30),
                metadata_={"topic_hint": topic_name, "demo": True},
            )
            batch.append(p)
            db.add(p)

        await db.flush()
        for p in batch:
            all_ids.append(p.id)
            # Determine topic from metadata
            post_topic_map[p.id] = p.metadata_.get("topic_hint", "fuel_prices")

        print(f"  + {min(batch_start + batch_size, TOTAL)}/{TOTAL} posts")

    await db.commit()
    return all_ids, post_topic_map


async def _seed_nlp(db: AsyncSession, post_ids: list[int], post_topic_map: dict[int, str]) -> None:
    print("\n[4/6] NLP results...")

    existing_r = await db.execute(text("SELECT post_id FROM post_nlp"))
    existing_set = {row[0] for row in existing_r.fetchall()}
    new_ids = [pid for pid in post_ids if pid not in existing_set]

    if not new_ids:
        print(f"  = NLP already complete for all posts")
        return

    batch_size = 300
    total_written = 0
    for i in range(0, len(new_ids), batch_size):
        chunk = new_ids[i:i + batch_size]
        for pid in chunk:
            topic = post_topic_map.get(pid, "fuel_prices")
            sentiment, score = _sentiment(topic)
            emotions = ["neutral", "anger", "joy", "fear", "sadness", "surprise"]
            emotion_weights = {
                "positive": [0.1, 0.05, 0.60, 0.05, 0.1, 0.1],
                "negative": [0.1, 0.45, 0.05, 0.20, 0.15, 0.05],
                "neutral":  [0.55, 0.10, 0.10, 0.10, 0.10, 0.05],
            }[sentiment]
            emotion = RNG.choices(emotions, weights=emotion_weights, k=1)[0]
            emotion_score = round(RNG.uniform(0.45, 0.88), 3)
            intensity = round(abs(score - 0.5) * 2, 3)

            nlp = PostNLP(
                post_id=pid,
                sentiment=sentiment,
                sentiment_score=score,
                emotion=emotion,
                emotion_score=emotion_score,
                support_score=score if sentiment == "positive" else 1.0 - score,
                intensity=intensity,
                sarcasm_flag=False,
                sarcasm_conf=round(RNG.uniform(0.02, 0.12), 3),
                model_version="rule-based-v1-demo",
            )
            db.add(nlp)
        await db.flush()
        total_written += len(chunk)
        print(f"  + NLP {total_written}/{len(new_ids)}")

    await db.commit()


async def _seed_post_topics(
    db: AsyncSession,
    post_ids: list[int],
    post_topic_map: dict[int, str],
    topic_ids: dict[str, int],
) -> None:
    print("\n[4b/6] Post-topic assignments...")

    existing_r = await db.execute(text("SELECT post_id FROM post_topics"))
    existing_set = {row[0] for row in existing_r.fetchall()}
    new_ids = [pid for pid in post_ids if pid not in existing_set]

    if not new_ids:
        print("  = Post-topic assignments already complete")
        return

    for pid in new_ids:
        topic_name = post_topic_map.get(pid, "fuel_prices")
        tid = topic_ids.get(topic_name)
        if tid is None:
            continue
        pt = PostTopic(
            post_id=pid,
            topic_id=tid,
            confidence=round(RNG.uniform(0.55, 0.92), 3),
        )
        db.add(pt)

    await db.flush()
    await db.commit()
    print(f"  + {len(new_ids)} post-topic rows")


async def _seed_trends(db: AsyncSession, topic_ids: dict[str, int]) -> None:
    print("\n[5/6] Trends...")

    existing_r = await db.execute(text("SELECT name FROM trends"))
    existing_names = {row[0] for row in existing_r.fetchall()}

    now = datetime.now(timezone.utc)
    for spec in _TREND_SPECS:
        if spec["name"] in existing_names:
            print(f"  = {spec['name']} (exists)")
            continue
        tid = topic_ids.get(spec["topic"])
        t = Trend(
            topic_id=tid,
            name=spec["name"],
            trend_score=spec["trend_score"],
            volume_decay=spec["baseline_7d"] * spec["trend_score"],
            velocity=spec["velocity"],
            acceleration=spec["acceleration"],
            engagement=round(RNG.uniform(0.04, 0.22), 3),
            unique_users=spec["unique_users"],
            platform_count=spec["platform_count"],
            community_spread=spec["community_spread"],
            sentiment_shift=spec["sentiment_shift"],
            baseline_7d=spec["baseline_7d"],
            is_emerging=spec["is_emerging"],
            platforms=spec["platforms"],
            measured_at=now,
        )
        db.add(t)
        print(f"  + {spec['name']}")

    await db.commit()


async def _seed_segments(db: AsyncSession) -> None:
    print("\n[6/6] Segments & Personas...")

    existing_r = await db.execute(text("SELECT name FROM demographic_segments"))
    existing_names = {row[0] for row in existing_r.fetchall()}

    for spec in _SEGMENT_SPECS:
        if spec["name"] in existing_names:
            print(f"  = {spec['name'][:60]}... (exists)")
            continue

        seg = DemographicSegment(
            name=spec["name"],
            description=spec["description"],
            dominant_language=spec["dominant_language"],
            size_estimate=spec["size_estimate"],
            confidence=spec["confidence"],
            evidence_count=RNG.randint(120, 480),
            topic_prefs=spec["topic_prefs"],
            sentiment_profile=spec["sentiment_profile"],
            activity_profile=spec["activity_profile"],
            geo_distribution=spec["geo_distribution"],
            updated_at=datetime.now(timezone.utc),
        )
        db.add(seg)
        await db.flush()

        persona = Persona(
            segment_id=seg.id,
            summary=spec["summary"],
            interests={"tags": spec["interests"]},
            reaction=spec["reaction"],
            influence_score=round(RNG.uniform(0.3, 0.8), 3),
            confidence=spec["confidence"],
            evidence_json={"post_sample_count": RNG.randint(60, 200)},
        )
        db.add(persona)
        print(f"  + {spec['name'][:60]}...")

    await db.commit()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    asyncio.run(seed(db_url))

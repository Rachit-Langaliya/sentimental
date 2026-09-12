"""
Policy Simulation Engine — Phase 5.

"Simulate before announce" — given a policy text, predicts how each
demographic segment will react, drawing on historical post patterns.

Pipeline (two modes):
  REAL  (USE_REAL_NLP=True)  — sentence-embedding similarity to find
         analogous posts, then aggregate their NLP outcomes per segment.
  MOCK  (default)            — keyword-based topic extraction, rule
         modifiers from segment profiles, deterministic synthetic output.

Either mode reads real DemographicSegment rows if they exist.  When
the DB has no segments yet, falls back to synthetic named segments so
the demo works from day-one without any ingested data.
"""
from __future__ import annotations

import hashlib
import math
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import DemographicSegment, Persona, Platform, PostNLP, RawPost, Trend
from app.schemas.schemas import SegmentSimulationResponse, SentimentBreakdown

logger = structlog.get_logger()

# ── Keyword banks for topic extraction ────────────────────────────────────────

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "fuel_prices":      ["fuel", "petrol", "diesel", "lpg", "gas", "oil", "energy", "price hike", "inflation", "पेट्रोल", "ईंधन"],
    "agriculture_msp":  ["farmer", "kisan", "msp", "crop", "agriculture", "agri", "farm", "subsidy", "irrigation", "किसान", "खेती", "फसल"],
    "ev_policy":        ["ev", "electric vehicle", "charging", "fame", "battery", "solar", "green", "clean energy", "emission"],
    "education_reform": ["education", "nep", "school", "student", "exam", "university", "fee", "scholarship", "board", "curriculum"],
    "healthcare":       ["health", "hospital", "medicine", "ayushman", "pmjay", "insurance", "doctor", "vaccine", "clinic"],
    "employment":       ["job", "employment", "unemployment", "skill", "startup", "gig", "work", "salary", "labour", "rozgar"],
    "ai_regulation":    ["ai", "artificial intelligence", "tech", "digital", "data", "privacy", "algorithm", "automation", "robot"],
    "taxation":         ["tax", "gst", "cess", "levy", "duty", "surcharge", "income tax", "corporate tax"],
    "infrastructure":   ["road", "highway", "railway", "metro", "airport", "port", "bridge", "smart city", "housing"],
    "social_welfare":   ["pension", "ration", "bpl", "welfare", "benefit", "scheme", "yojana", "direct benefit", "dbt"],
}

_TOPIC_DISPLAY = {
    "fuel_prices": "Fuel & Energy Prices",
    "agriculture_msp": "Agriculture & MSP",
    "ev_policy": "Electric Vehicles",
    "education_reform": "Education Reform",
    "healthcare": "Healthcare",
    "employment": "Employment & Jobs",
    "ai_regulation": "AI & Technology",
    "taxation": "Taxation",
    "infrastructure": "Infrastructure",
    "social_welfare": "Social Welfare",
}

# Sentiment modifier: how each topic biases reaction (+ve modifier → more support)
_TOPIC_SENTIMENT_BIAS: dict[str, float] = {
    "fuel_prices":      -0.25,   # hikes almost always negative
    "agriculture_msp":  +0.15,   # MSP increases are popular
    "ev_policy":        +0.10,
    "education_reform": -0.05,   # change → anxiety, but reform can be positive
    "healthcare":       +0.08,
    "employment":       +0.05,
    "ai_regulation":    -0.08,   # uncertain / feared
    "taxation":         -0.20,
    "infrastructure":   +0.12,
    "social_welfare":   +0.18,
}

# Keyword sentiment modifiers (applied on top of topic bias)
_POSITIVE_SIGNALS = ["increase", "expand", "benefit", "free", "reduce tax", "subsidy", "support",
                     "relief", "waiver", "boost", "new scheme", "launch", "improve", "yojana"]
_NEGATIVE_SIGNALS = ["hike", "cut", "remove", "ban", "compulsory", "mandatory", "increase tax",
                     "cess", "penalty", "fee", "charge", "withdraw", "reduce subsidy"]

# Narrative templates keyed by (topic, sentiment)
_NARRATIVES: dict[tuple[str, str], list[str]] = {
    ("fuel_prices", "negative"):      ["cost of living concerns", "impact on daily commute", "burden on middle class", "inflation fears", "comparison with previous hikes"],
    ("fuel_prices", "neutral"):       ["wait-and-watch stance", "government revenue justification", "demand for transparency"],
    ("fuel_prices", "positive"):      ["environmental benefit framing", "clean energy transition support"],
    ("agriculture_msp", "positive"):  ["farmer income improvement", "MSP as fair price", "rural economy boost", "support for Kisan"],
    ("agriculture_msp", "negative"):  ["implementation doubts", "middlemen exploitation concern", "procurement delay fears"],
    ("ev_policy", "positive"):        ["clean energy transition", "fuel cost savings", "import reduction", "green India narrative"],
    ("ev_policy", "negative"):        ["charging infrastructure gaps", "high upfront cost", "range anxiety", "rural access concerns"],
    ("education_reform", "negative"): ["student anxiety about change", "teacher training concerns", "exam pattern confusion", "syllabus overload"],
    ("education_reform", "positive"): ["skill-based learning support", "NEP alignment", "vocational training emphasis"],
    ("healthcare", "positive"):       ["universal health coverage", "Ayushman Bharat support", "affordable medicine demand"],
    ("healthcare", "negative"):       ["private hospital concerns", "medicine cost fears", "rural access gaps"],
    ("employment", "positive"):       ["job creation narrative", "startup ecosystem growth", "skill India support"],
    ("employment", "negative"):       ["automation job loss fears", "gig worker rights concern", "wage stagnation"],
    ("taxation", "negative"):         ["taxpayer burden", "small business impact", "disposable income reduction", "compliance complexity"],
    ("taxation", "positive"):         ["revenue for development", "simplified structure support"],
    ("infrastructure", "positive"):   ["connectivity improvement", "economic growth catalyst", "smart city vision"],
    ("social_welfare", "positive"):   ["direct benefit transfer support", "poverty alleviation", "beneficiary reach"],
}
_DEFAULT_NARRATIVES = ["policy impact discussion", "wait for implementation details", "demand for public consultation"]


# ── Main entry point ───────────────────────────────────────────────────────────

async def simulate(db: AsyncSession, policy_text: str) -> dict[str, Any]:
    """
    Run the simulation and return a dict matching SimulationResult fields.
    """
    topics = _extract_topics(policy_text)
    sentiment_bias = _compute_policy_bias(policy_text, topics)

    # Load real segments (or generate synthetic ones)
    segments = await _load_segments(db)

    # Find analogous posts from DB
    analogues = await _find_analogues(db, topics, limit=200)

    # Compute per-segment responses
    segment_responses = []
    for seg in segments:
        resp = _predict_segment_response(seg, policy_text, topics, sentiment_bias, analogues)
        segment_responses.append(resp)

    # Overall sentiment = weighted average by segment size
    overall = _weighted_overall(segment_responses, segments)

    # Influential communities from persona influence scores
    influential = await _influential_communities(db, segments, topics)

    # Potential spread based on platform + analogue volume
    spread = _estimate_spread(analogues, segments)

    # Analogues used (display names)
    analogue_names = _analogue_labels(analogues, topics)

    return {
        "topics_detected": [_TOPIC_DISPLAY.get(t, t) for t in topics],
        "overall_sentiment": overall,
        "overall_confidence": _overall_confidence(segment_responses, analogues),
        "analogues_used": analogue_names,
        "segment_responses": segment_responses,
        "influential_communities": influential,
        "potential_spread": spread,
    }


# ── Topic extraction ───────────────────────────────────────────────────────────

def _extract_topics(text: str) -> list[str]:
    lower = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in _TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[topic] = score
    if not scores:
        return ["social_welfare"]  # default
    # Return up to 3 top topics
    return sorted(scores, key=scores.get, reverse=True)[:3]  # type: ignore[arg-type]


def _compute_policy_bias(text: str, topics: list[str]) -> float:
    """Overall sentiment bias of this policy (-1 very negative, +1 very positive)."""
    lower = text.lower()
    bias = sum(_TOPIC_SENTIMENT_BIAS.get(t, 0.0) for t in topics) / max(len(topics), 1)
    pos_hits = sum(1 for s in _POSITIVE_SIGNALS if s in lower)
    neg_hits = sum(1 for s in _NEGATIVE_SIGNALS if s in lower)
    bias += pos_hits * 0.08 - neg_hits * 0.10
    return max(-0.8, min(0.8, bias))


# ── Analogue finder ────────────────────────────────────────────────────────────

async def _find_analogues(db: AsyncSession, topics: list[str], limit: int = 200) -> list[Any]:
    """
    Find historical posts about the same topics with their NLP results.
    Returns list of Row objects with (sentiment, support_score, intensity, platform_id).
    """
    now = datetime.now(timezone.utc)
    window = now - timedelta(days=90)
    rows_r = await db.execute(
        select(
            PostNLP.sentiment,
            PostNLP.support_score,
            PostNLP.intensity,
            RawPost.platform_id,
            RawPost.metadata_,
        )
        .join(RawPost, RawPost.id == PostNLP.post_id)
        .where(RawPost.post_ts >= window)
        .where(RawPost.expires_at > now)
        .order_by(RawPost.post_ts.desc())
        .limit(limit * 4)  # over-fetch, then filter by topic
    )
    rows = rows_r.all()

    # Filter to matching topics
    matched = [r for r in rows if (r.metadata_ or {}).get("topic") in topics]
    if len(matched) < 10:
        matched = rows  # fall back to all if not enough topic matches

    return matched[:limit]


# ── Segment prediction ─────────────────────────────────────────────────────────

def _predict_segment_response(
    seg: DemographicSegment,
    policy_text: str,
    topics: list[str],
    sentiment_bias: float,
    analogues: list[Any],
) -> SegmentSimulationResponse:
    """
    Predict this segment's reaction using:
      1. Segment's historical sentiment profile (base)
      2. Segment's topic_prefs affinity (modifier)
      3. Policy sentiment bias (modifier)
      4. Analogue post sentiment (modifier, weighted by count)
    """
    # Deterministic seed for reproducible demo output
    seed = int(hashlib.md5(f"{seg.id}{policy_text[:30]}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    sp = seg.sentiment_profile or {"positive": 0.33, "neutral": 0.34, "negative": 0.33}
    base_pos = sp.get("positive", 0.33)
    base_neg = sp.get("negative", 0.33)

    # Topic affinity: how much does this segment care about these topics?
    tp = seg.topic_prefs or {}
    topic_affinity = sum(
        tp.get(_TOPIC_DISPLAY.get(t, t), tp.get(t, 0.0))
        for t in topics
    ) / max(len(topics), 1)
    topic_affinity = min(topic_affinity * 3, 1.0)  # scale to [0,1]

    # Analogue sentiment
    if analogues:
        ana_pos = sum(1 for a in analogues if a.sentiment == "positive") / len(analogues)
        ana_neg = sum(1 for a in analogues if a.sentiment == "negative") / len(analogues)
        analogue_bias = ana_pos - ana_neg  # in [-1, 1]
    else:
        analogue_bias = 0.0

    # Combine: 40% base, 30% analogue, 30% policy bias
    combined_bias = 0.40 * (base_pos - base_neg) + 0.30 * analogue_bias + 0.30 * sentiment_bias

    # Convert bias to (pos, neg, neu) distribution
    pos = max(0.05, min(0.80, 0.33 + combined_bias * 0.6 + rng.uniform(-0.04, 0.04)))
    neg = max(0.05, min(0.80, 0.33 - combined_bias * 0.5 + rng.uniform(-0.04, 0.04)))
    total = pos + neg
    if total > 0.90:
        scale = 0.90 / total
        pos, neg = pos * scale, neg * scale
    neu = max(0.05, 1.0 - pos - neg)

    expected_sent = "positive" if pos > neg + 0.05 else ("negative" if neg > pos + 0.05 else "neutral")

    # Intensity: topic affinity amplifies engagement
    base_intensity = (analogues and
                      sum(a.intensity or 0.5 for a in analogues[:20]) / min(len(analogues), 20)) or 0.55
    intensity = min(0.95, base_intensity + topic_affinity * 0.25 + rng.uniform(-0.05, 0.05))

    # Support ratio
    support = max(0.02, min(0.90, pos + rng.uniform(-0.08, 0.08)))

    # Confidence: higher when we have analogues and the segment has good evidence
    evidence_factor = min(seg.evidence_count / 500, 0.4) if seg.evidence_count else 0.1
    analogue_factor = min(len(analogues) / 100, 0.35)
    confidence = max(0.40, min(0.90, 0.35 + evidence_factor + analogue_factor + rng.uniform(-0.05, 0.05)))

    # Narratives
    narratives = _pick_narratives(topics, expected_sent, rng)

    return SegmentSimulationResponse(
        segment_id=seg.id,
        segment_name=seg.name,
        expected_sentiment=expected_sent,
        sentiment_distribution=SentimentBreakdown(
            positive=round(pos, 3),
            neutral=round(neu, 3),
            negative=round(neg, 3),
        ),
        intensity=round(intensity, 3),
        support_ratio=round(support, 3),
        likely_narratives=narratives,
        confidence=round(confidence, 3),
        evidence_count=len(analogues),
    )


def _pick_narratives(topics: list[str], sentiment: str, rng: random.Random) -> list[str]:
    pool: list[str] = []
    for topic in topics:
        pool.extend(_NARRATIVES.get((topic, sentiment), []))
    if not pool:
        pool = _DEFAULT_NARRATIVES
    pool = list(dict.fromkeys(pool))  # deduplicate preserving order
    return rng.sample(pool, k=min(3, len(pool)))


# ── Aggregation helpers ────────────────────────────────────────────────────────

def _weighted_overall(
    responses: list[SegmentSimulationResponse],
    segments: list[DemographicSegment],
) -> SentimentBreakdown:
    if not responses:
        return SentimentBreakdown(positive=0.33, neutral=0.34, negative=0.33)

    sizes = {s.id: (s.size_estimate or 1) for s in segments}
    total_weight = 0.0
    w_pos = w_neu = w_neg = 0.0

    for r in responses:
        w = sizes.get(r.segment_id, 1)
        total_weight += w
        w_pos += r.sentiment_distribution.positive * w
        w_neu += r.sentiment_distribution.neutral * w
        w_neg += r.sentiment_distribution.negative * w

    tw = total_weight or 1
    return SentimentBreakdown(
        positive=round(w_pos / tw, 3),
        neutral=round(w_neu / tw, 3),
        negative=round(w_neg / tw, 3),
    )


def _overall_confidence(
    responses: list[SegmentSimulationResponse],
    analogues: list[Any],
) -> float:
    if not responses:
        return 0.45
    base = sum(r.confidence for r in responses) / len(responses)
    analogue_bonus = min(len(analogues) / 200, 0.15)
    return round(min(0.88, base + analogue_bonus), 3)


async def _influential_communities(
    db: AsyncSession,
    segments: list[DemographicSegment],
    topics: list[str],
) -> list[str]:
    """
    Return up to 6 community labels most likely to amplify this policy topic.
    Uses persona influence scores + platform distribution from trending topics.
    """
    # Segment names that align with these topics
    topic_display = {_TOPIC_DISPLAY.get(t, t).lower() for t in topics}

    communities: list[tuple[float, str]] = []
    for seg in segments:
        if not seg.name:
            continue
        # Check if segment's top topic overlaps with policy topics
        tp = seg.topic_prefs or {}
        affinity = sum(
            v for k, v in tp.items()
            if any(td in k.lower() for td in topic_display)
        )
        influence = 0.5
        # Use personas if available
        persona_r = await db.execute(
            select(Persona)
            .where(Persona.segment_id == seg.id)
            .order_by(Persona.generated_at.desc())
            .limit(1)
        )
        persona = persona_r.scalar_one_or_none()
        if persona and persona.influence_score:
            influence = persona.influence_score

        score = influence * (1 + affinity)
        # Extract a short community label from segment name
        label = _community_label(seg.name)
        communities.append((score, label))

    communities.sort(reverse=True)
    seen: set[str] = set()
    result = []
    for _, label in communities:
        if label not in seen:
            seen.add(label)
            result.append(label)
        if len(result) >= 6:
            break

    # Pad with generic labels if needed
    _GENERIC = ["urban-middle-class", "student-communities", "rural-farmers",
                "transport-workers", "small-business-owners", "youth-twitter"]
    for g in _GENERIC:
        if len(result) >= 6:
            break
        if g not in result:
            result.append(g)

    return result[:6]


def _community_label(segment_name: str) -> str:
    """Extract a short slug from a segment name like 'Hindi-speaking Twitter users...'"""
    # "Hindi-speaking Twitter users interested in Fuel & Energy"
    # → "hindi-twitter-fuel"
    name = segment_name.lower()
    parts = []
    for lang in ["english", "hindi", "tamil", "telugu", "bengali", "marathi"]:
        if lang in name:
            parts.append(lang)
            break
    for plat in ["twitter", "facebook", "instagram", "telegram", "reddit", "youtube"]:
        if plat in name:
            parts.append(plat)
            break
    # topic keyword
    for topic_disp in _TOPIC_DISPLAY.values():
        if topic_disp.lower().split()[0] in name:
            parts.append(topic_disp.lower().replace(" & ", "-").replace(" ", "-").split("-")[0])
            break
    return "-".join(parts) if parts else segment_name[:20].lower().replace(" ", "-")


def _estimate_spread(analogues: list[Any], segments: list[DemographicSegment]) -> str:
    """Estimate virality: high / medium / low based on platform count and analogue volume."""
    if not analogues and not segments:
        return "medium"

    platform_ids = {a.platform_id for a in analogues if a.platform_id}
    platform_count = len(platform_ids)
    total_size = sum(s.size_estimate or 0 for s in segments)
    analogue_count = len(analogues)

    score = (platform_count * 0.3) + (min(analogue_count, 100) / 100 * 0.4) + (min(total_size, 500) / 500 * 0.3)
    if score > 0.6:
        return "high"
    if score > 0.3:
        return "medium"
    return "low"


def _analogue_labels(analogues: list[Any], topics: list[str]) -> list[str]:
    """Return human-readable analogue event names for display."""
    if not analogues:
        # Synthetic fallback labels
        _SYNTH: dict[str, list[str]] = {
            "fuel_prices":      ["2022 fuel price hike debate", "2021 LPG price revision", "2019 petrol crisis"],
            "agriculture_msp":  ["2021 farm laws protest", "2020 MSP demand agitation", "2018 kisan rally"],
            "ev_policy":        ["2023 EV subsidy announcement", "2022 FAME-II extension", "2021 EV mandate debate"],
            "education_reform": ["2020 NEP rollout", "2023 CUET controversy", "2022 board exam delay"],
            "healthcare":       ["2023 Ayushman expansion", "2022 medicine price cap", "2021 vaccine rollout"],
            "employment":       ["2023 gig worker rights bill", "2022 unemployment data dispute", "2021 MGNREGS fund cut"],
            "taxation":         ["2023 GST revision", "2022 income tax slab change", "2021 surcharge debate"],
            "social_welfare":   ["2023 DBT expansion", "2022 ration card linkage", "2021 PM-KISAN 6th instalment"],
        }
        labels: list[str] = []
        for t in topics:
            labels.extend(_SYNTH.get(t, [])[:2])
        return labels[:4] if labels else ["recent-policy-discourse", "budget-2024-debate"]

    # Derive from actual data: use the topics present in analogues
    topic_counts: defaultdict[str, int] = defaultdict(int)
    for a in analogues:
        t = (a.metadata_ or {}).get("topic", "unknown")
        topic_counts[t] += 1

    labels = []
    for t, cnt in sorted(topic_counts.items(), key=lambda x: -x[1])[:3]:
        name = _TOPIC_DISPLAY.get(t, t.replace("_", " ").title())
        labels.append(f"{name} discourse ({cnt} posts)")
    return labels


# ── Synthetic segment fallback ─────────────────────────────────────────────────

async def _load_segments(db: AsyncSession) -> list[DemographicSegment]:
    result = await db.execute(
        select(DemographicSegment).order_by(DemographicSegment.evidence_count.desc()).limit(8)
    )
    segments = result.scalars().all()
    if segments:
        return list(segments)
    # Return synthetic segments when DB is empty (cold-start demo)
    return _synthetic_segments()


def _synthetic_segments() -> list[DemographicSegment]:
    """Pre-built representative segments for demo when no ingestion has run."""
    PROFILES = [
        {"name": "Hindi-speaking Twitter users interested in Fuel & Energy Prices",
         "dominant_language": "Hindi", "size_estimate": 420, "evidence_count": 1850,
         "confidence": 0.72, "topic_prefs": {"Fuel & Energy": 0.38, "Agriculture & MSP": 0.18},
         "sentiment_profile": {"positive": 0.22, "neutral": 0.35, "negative": 0.43}},
        {"name": "English-speaking Reddit users interested in AI & Technology",
         "dominant_language": "English", "size_estimate": 280, "evidence_count": 940,
         "confidence": 0.68, "topic_prefs": {"AI & Technology": 0.45, "Employment & Jobs": 0.22},
         "sentiment_profile": {"positive": 0.38, "neutral": 0.42, "negative": 0.20}},
        {"name": "Tamil-speaking Facebook users interested in Agriculture & MSP",
         "dominant_language": "Tamil", "size_estimate": 360, "evidence_count": 1320,
         "confidence": 0.65, "topic_prefs": {"Agriculture & MSP": 0.52, "Healthcare": 0.14},
         "sentiment_profile": {"positive": 0.28, "neutral": 0.31, "negative": 0.41}},
        {"name": "English-speaking YouTube users interested in Electric Vehicles",
         "dominant_language": "English", "size_estimate": 190, "evidence_count": 680,
         "confidence": 0.61, "topic_prefs": {"Electric Vehicles": 0.48, "AI & Technology": 0.18},
         "sentiment_profile": {"positive": 0.45, "neutral": 0.38, "negative": 0.17}},
        {"name": "Hindi-speaking Instagram users interested in Education Reform",
         "dominant_language": "Hindi", "size_estimate": 310, "evidence_count": 1100,
         "confidence": 0.63, "topic_prefs": {"Education Reform": 0.41, "Employment & Jobs": 0.25},
         "sentiment_profile": {"positive": 0.30, "neutral": 0.38, "negative": 0.32}},
        {"name": "Telugu-speaking Facebook users interested in Healthcare",
         "dominant_language": "Telugu", "size_estimate": 245, "evidence_count": 870,
         "confidence": 0.60, "topic_prefs": {"Healthcare": 0.44, "Social Welfare": 0.20},
         "sentiment_profile": {"positive": 0.34, "neutral": 0.40, "negative": 0.26}},
    ]
    segs = []
    for i, p in enumerate(PROFILES, start=1):
        s = DemographicSegment()
        s.id = i
        for k, v in p.items():
            setattr(s, k, v)
        s.updated_at = datetime.now(timezone.utc)
        segs.append(s)
    return segs

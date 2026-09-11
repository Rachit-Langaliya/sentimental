"""
Trend Engine — Phase 3.
Computes composite trend scores from ingested posts + NLP results.

Score formula:
  trend_score = 0.30 * vol_norm + 0.20 * vel_norm + 0.15 * acc_norm
              + 0.15 * eng_norm + 0.10 * users_norm
              + 0.05 * platform_norm + 0.05 * community_spread

Time-decay volume: V(t) = Σᵢ exp(-λ * (now - tᵢ).total_seconds() / 3600)
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select, distinct, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Platform, PostNLP, RawPost, Trend, Topic

logger = structlog.get_logger()

# Decay constant λ (higher = faster decay, shorter-lived topics)
_LAMBDA_DEFAULT = 0.25
_COMPOSITE_WEIGHTS = (0.30, 0.20, 0.15, 0.15, 0.10, 0.05, 0.05)


async def recompute_trends(db: AsyncSession) -> int:
    """
    Main entry point — computes trend scores for all discovered topics
    from the past 7 days and upserts to the Trend table.
    Returns the number of topics updated.
    """
    now = datetime.now(timezone.utc)
    window_7d = now - timedelta(days=7)
    window_24h = now - timedelta(hours=24)
    window_6h = now - timedelta(hours=6)
    window_12h = now - timedelta(hours=12)

    # Fetch all posts in the 7-day window with their metadata topic
    rows_r = await db.execute(
        select(
            RawPost.id,
            RawPost.post_ts,
            RawPost.author_hash,
            RawPost.platform_id,
            RawPost.metadata_,
            PostNLP.sentiment,
        )
        .outerjoin(PostNLP, PostNLP.post_id == RawPost.id)
        .where(RawPost.post_ts >= window_7d)
        .where(RawPost.expires_at > now)
    )
    posts = rows_r.all()

    if not posts:
        return 0

    # Group by topic (from metadata_.topic field set by connectors)
    groups: dict[str, list] = {}
    for row in posts:
        topic_key = (row.metadata_ or {}).get("topic", "unknown")
        groups.setdefault(topic_key, []).append(row)

    # Get platform id → name map
    plat_r = await db.execute(select(Platform))
    plat_map = {p.id: p.name for p in plat_r.scalars().all()}

    # Compute max values for normalisation
    raw_scores: dict[str, dict] = {}
    for topic_key, topic_posts in groups.items():
        raw_scores[topic_key] = _compute_raw(topic_posts, now, window_6h, window_12h, window_24h, plat_map)

    # Normalise across topics
    metrics = ["volume_decay", "velocity", "acceleration", "engagement", "unique_users"]
    max_vals = {m: max((raw_scores[t][m] for t in raw_scores), default=1.0) or 1.0 for m in metrics}
    max_platforms = max((raw_scores[t]["platform_count"] for t in raw_scores), default=1) or 1

    all_scores = []
    trend_data: dict[str, dict] = {}
    for topic_key, rs in raw_scores.items():
        vol_n  = rs["volume_decay"] / max_vals["volume_decay"]
        vel_n  = rs["velocity"] / max_vals["velocity"]
        acc_n  = rs["acceleration"] / max_vals["acceleration"]
        eng_n  = rs["engagement"] / max_vals["engagement"]
        usr_n  = rs["unique_users"] / max_vals["unique_users"]
        plt_n  = rs["platform_count"] / max_platforms
        spr    = rs["community_spread"]

        score = (
            _COMPOSITE_WEIGHTS[0] * vol_n +
            _COMPOSITE_WEIGHTS[1] * vel_n +
            _COMPOSITE_WEIGHTS[2] * acc_n +
            _COMPOSITE_WEIGHTS[3] * eng_n +
            _COMPOSITE_WEIGHTS[4] * usr_n +
            _COMPOSITE_WEIGHTS[5] * plt_n +
            _COMPOSITE_WEIGHTS[6] * spr
        )
        all_scores.append(score)
        trend_data[topic_key] = {**rs, "trend_score": round(score, 4), "volume_decay_norm": vol_n}

    # Emerging detection: score > mean + 1.5 * std
    if all_scores:
        mean = sum(all_scores) / len(all_scores)
        std = math.sqrt(sum((s - mean) ** 2 for s in all_scores) / len(all_scores))
        emerging_threshold = mean + 1.5 * std
    else:
        emerging_threshold = 0.7

    # Upsert to Trend table
    _TOPIC_DISPLAY = {
        "fuel_prices": "Fuel & Energy Prices",
        "ai_regulation": "AI & Technology Policy",
        "agriculture_msp": "Agriculture & MSP",
        "ev_policy": "Electric Vehicles",
        "education_reform": "Education Reform",
        "healthcare": "Healthcare Policy",
        "employment": "Employment & Jobs",
        "unknown": "General Discussion",
    }

    upserted = 0
    for topic_key, td in trend_data.items():
        name = _TOPIC_DISPLAY.get(topic_key, topic_key.replace("_", " ").title())

        # Find or create topic row
        existing_trend_r = await db.execute(select(Trend).where(Trend.name == name))
        existing_trend = existing_trend_r.scalar_one_or_none()

        trend_obj = existing_trend or Trend()
        trend_obj.name = name
        trend_obj.trend_score = td["trend_score"]
        trend_obj.volume_decay = round(td["volume_decay"], 4)
        trend_obj.velocity = round(td["velocity"], 4)
        trend_obj.acceleration = round(td["acceleration"], 4)
        trend_obj.engagement = round(td["engagement"], 4)
        trend_obj.unique_users = td["unique_users"]
        trend_obj.platform_count = td["platform_count"]
        trend_obj.community_spread = round(td["community_spread"], 4)
        trend_obj.sentiment_shift = round(td["sentiment_shift"], 4)
        trend_obj.baseline_7d = round(td["baseline_7d"], 4)
        trend_obj.is_emerging = td["trend_score"] >= emerging_threshold
        trend_obj.platforms = td["platforms"]
        trend_obj.measured_at = now

        if not existing_trend:
            db.add(trend_obj)
        upserted += 1

    await db.commit()
    logger.info("trends_recomputed", count=upserted)
    return upserted


def _compute_raw(
    posts: list,
    now: datetime,
    window_6h: datetime,
    window_12h: datetime,
    window_24h: datetime,
    plat_map: dict[int, str],
) -> dict:
    """Compute raw (un-normalised) metrics for one topic group."""
    # Time-decay volume (24h window)
    volume_decay = sum(
        math.exp(-_LAMBDA_DEFAULT * (now - p.post_ts).total_seconds() / 3600)
        for p in posts if p.post_ts >= window_24h
    )

    # Velocity: posts in last 6h vs prior 6h
    recent_6h = [p for p in posts if p.post_ts >= window_6h]
    prior_6h = [p for p in posts if window_12h <= p.post_ts < window_6h]
    velocity = max(0.0, len(recent_6h) - len(prior_6h)) / 6.0

    # Acceleration (second derivative)
    quarter = timedelta(hours=1.5)
    t0, t1 = now - timedelta(hours=3), now - timedelta(hours=6)
    q1 = sum(1 for p in posts if (now - quarter) <= p.post_ts <= now)
    q2 = sum(1 for p in posts if t0 <= p.post_ts < (now - quarter))
    q3 = sum(1 for p in posts if t1 <= p.post_ts < t0)
    v_curr = q1 - q2
    v_prev = q2 - q3
    acceleration = max(0.0, v_curr - v_prev) / 1.5

    # Engagement: from metadata (likes, retweets, etc.)
    eng_scores = []
    for p in posts:
        meta = p.metadata_ or {}
        eng = (meta.get("like_count", 0) + meta.get("retweet_count", 0) * 2 +
               meta.get("views", 0) * 0.01 + meta.get("score", 0) * 0.5)
        if eng > 0:
            eng_scores.append(math.log1p(eng))
    engagement = sum(eng_scores) / len(eng_scores) if eng_scores else 0.0

    # Unique users (distinct author_hashes)
    unique_users = len({p.author_hash for p in posts if p.author_hash})

    # Platform stats
    platform_names = [plat_map.get(p.platform_id, "unknown") for p in posts]
    platform_set = set(platform_names)
    platform_count = len(platform_set)

    # Community spread: normalised entropy of platform distribution
    if platform_count > 1:
        from collections import Counter
        counts = Counter(platform_names)
        total = len(platform_names)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        max_entropy = math.log2(platform_count)
        community_spread = entropy / max_entropy if max_entropy > 0 else 0.0
    else:
        community_spread = 0.0

    # Sentiment shift: avg recent 6h sentiment vs 24h baseline
    def _avg_pos(subset):
        pos = [1 for p in subset if p.sentiment == "positive"]
        return len(pos) / max(len(subset), 1)

    sent_recent = _avg_pos(recent_6h)
    sent_24h_all = _avg_pos([p for p in posts if p.post_ts >= window_24h])
    sentiment_shift = sent_recent - sent_24h_all

    # 7-day baseline volume
    baseline_7d = len(posts) / 7.0

    return {
        "volume_decay": max(volume_decay, 0.001),
        "velocity": max(velocity, 0.0),
        "acceleration": max(acceleration, 0.0),
        "engagement": max(engagement, 0.0),
        "unique_users": unique_users,
        "platform_count": platform_count,
        "community_spread": round(community_spread, 4),
        "sentiment_shift": sentiment_shift,
        "baseline_7d": baseline_7d,
        "platforms": sorted(platform_set),
    }

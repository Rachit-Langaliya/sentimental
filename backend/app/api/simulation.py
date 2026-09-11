import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.core.config import settings
from app.models.models import AuditLog, DemographicSegment
from app.schemas.schemas import (
    SegmentSimulationResponse,
    SentimentBreakdown,
    SimulationRequest,
    SimulationResult,
)

router = APIRouter()

_DISCLAIMER = (
    "This is probabilistic scenario synthesis based on historical aggregate patterns, "
    "not a prediction of individual behaviour. Results should be used as one input "
    "among many for policy deliberation. Confidence intervals are wide. "
    "⚠ Phase 1 — using mock simulation engine. Full RAG engine wired in Phase 8."
)


@router.post("/run", response_model=SimulationResult)
async def run_simulation(body: SimulationRequest, current_user: CurrentUser, db: DB):
    # Audit log the query (hash only — never store raw policy text)
    query_hash = hashlib.sha256(body.policy_text.encode()).hexdigest()[:16]
    db.add(AuditLog(user_id=current_user.id, action="simulation_run", resource="simulation", query_hash=query_hash))
    await db.commit()

    # Fetch segments
    result = await db.execute(
        select(DemographicSegment).order_by(DemographicSegment.evidence_count.desc()).limit(6)
    )
    segments = result.scalars().all()

    segment_responses = [_mock_segment_response(s, body.policy_text) for s in segments]

    return SimulationResult(
        id=str(uuid.uuid4())[:8],
        policy_text=body.policy_text,
        overall_sentiment=SentimentBreakdown(positive=0.18, neutral=0.31, negative=0.51),
        overall_confidence=0.68,
        analogues_used=["2022-fuel-price-hike", "2021-lpu-tax-debate", "2019-petrol-crisis"],
        segment_responses=segment_responses,
        influential_communities=["student-forums", "transport-workers", "middle-class-urban"],
        potential_spread="high",
        disclaimer=_DISCLAIMER,
        generated_at=datetime.now(timezone.utc),
        mode="cloud",
    )


def _mock_segment_response(segment: DemographicSegment, policy_text: str) -> SegmentSimulationResponse:
    """Phase 1 mock — Phase 8 replaces with real RAG + LLM synthesis."""
    import random, hashlib

    # Deterministic randomness per segment for consistent demo output
    seed = int(hashlib.md5(f"{segment.id}{policy_text[:20]}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    sentiments = ["negative", "negative", "negative", "neutral", "positive"]
    sentiment = sentiments[rng.randint(0, len(sentiments) - 1)]

    neg = rng.uniform(0.38, 0.65)
    pos = rng.uniform(0.10, 0.25)
    neu = 1.0 - neg - pos

    return SegmentSimulationResponse(
        segment_id=segment.id,
        segment_name=segment.name,
        expected_sentiment=sentiment,
        sentiment_distribution=SentimentBreakdown(positive=round(pos, 2), neutral=round(neu, 2), negative=round(neg, 2)),
        intensity=round(rng.uniform(0.55, 0.85), 2),
        support_ratio=round(rng.uniform(0.08, 0.25), 2),
        likely_narratives=_pick_narratives(policy_text, rng),
        confidence=round(rng.uniform(0.58, 0.82), 2),
        evidence_count=segment.evidence_count,
    )


def _pick_narratives(policy_text: str, rng: "random.Random") -> list[str]:
    all_narratives = [
        "cost of living concerns",
        "impact on daily commute",
        "burden on middle class",
        "government revenue justification",
        "inflation fears",
        "student and youth impact",
        "demand for alternative policy",
        "comparison with previous hikes",
    ]
    return rng.sample(all_narratives, k=3)

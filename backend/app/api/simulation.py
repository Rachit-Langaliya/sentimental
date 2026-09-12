import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.models.models import AuditLog
from app.schemas.schemas import SimulationRequest, SimulationResult, SegmentSimulationResponse

router = APIRouter()

_DISCLAIMER = (
    "This is probabilistic scenario synthesis based on historical aggregate patterns, "
    "not a prediction of individual behaviour. Results should be used as one input "
    "among many for policy deliberation. Confidence intervals are wide. "
    "All analysis is performed on anonymised, aggregated data — no individual is identified. "
    "Results carry MODELED epistemic status."
)


@router.post("/run", response_model=SimulationResult)
async def run_simulation(body: SimulationRequest, current_user: CurrentUser, db: DB):
    """
    Predict public reaction to a policy or announcement.

    Pipeline:
      1. Extract topics from policy text (keyword matching)
      2. Find analogous historical posts from the DB
      3. For each demographic segment, combine base sentiment profile +
         topic affinity + analogue patterns + policy bias
      4. Compute weighted-average overall response
      5. Optionally: enrich narratives and produce executive brief via Ollama
         (set use_local_llm=true in request — requires Ollama to be running)

    Works in cold-start mode (no ingested data) using synthetic representative segments.
    """
    from app.services.simulation_engine import simulate

    # Audit log — hash only, never store raw policy text
    query_hash = hashlib.sha256(body.policy_text.encode()).hexdigest()[:16]
    db.add(AuditLog(
        user_id=current_user.id,
        action="simulation_run",
        resource="simulation",
        query_hash=query_hash,
    ))
    await db.commit()

    result = await simulate(db, body.policy_text)

    segment_responses: list[SegmentSimulationResponse] = result["segment_responses"]
    llm_brief: str | None = None
    mode = "cloud"

    # ── Optional Ollama enrichment ────────────────────────────────────────────
    if body.use_local_llm:
        from app.services import ollama_client
        if await ollama_client.is_available():
            mode = "local-llm"

            # Enrich each segment's likely_narratives via LLM
            for seg_resp in segment_responses:
                enriched = await ollama_client.generate_narratives(
                    segment_name=seg_resp.segment_name,
                    policy_text=body.policy_text,
                    topics=result.get("topics_detected", []),
                    expected_sentiment=seg_resp.expected_sentiment,
                )
                if enriched:
                    # Merge: keep up to 3 original + up to 3 LLM narratives
                    merged = list(dict.fromkeys(
                        seg_resp.likely_narratives[:3] + enriched[:3]
                    ))
                    seg_resp.likely_narratives = merged

            # Generate executive brief
            seg_summaries = [
                f"{r.segment_name}: {r.expected_sentiment} "
                f"({round(r.support_ratio * 100)}% support)"
                for r in segment_responses[:6]
            ]
            llm_brief = await ollama_client.generate_policy_brief(
                policy_text=body.policy_text,
                overall_sentiment={
                    "positive": result["overall_sentiment"].positive,
                    "neutral":  result["overall_sentiment"].neutral,
                    "negative": result["overall_sentiment"].negative,
                },
                potential_spread=result["potential_spread"],
                overall_confidence=result["overall_confidence"],
                segment_summaries=seg_summaries,
            )

    return SimulationResult(
        id=str(uuid.uuid4())[:8],
        policy_text=body.policy_text,
        overall_sentiment=result["overall_sentiment"],
        overall_confidence=result["overall_confidence"],
        analogues_used=result["analogues_used"],
        topics_detected=result.get("topics_detected", []),
        segment_responses=segment_responses,
        influential_communities=result["influential_communities"],
        potential_spread=result["potential_spread"],
        llm_brief=llm_brief,
        disclaimer=_DISCLAIMER,
        generated_at=datetime.now(timezone.utc),
        mode=mode,
    )

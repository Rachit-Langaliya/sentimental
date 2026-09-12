from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.models import UserRole


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# ── Platform ──────────────────────────────────────────────────────────────────

class PlatformRead(BaseModel):
    id: int
    name: str
    display_name: str
    api_status: str
    color: Optional[str] = None
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Dashboard summary ─────────────────────────────────────────────────────────

class SentimentBreakdown(BaseModel):
    positive: float
    neutral: float
    negative: float


class TimePoint(BaseModel):
    timestamp: datetime
    positive: float
    neutral: float
    negative: float


class PlatformStat(BaseModel):
    platform: str
    display_name: str
    post_count: int
    color: Optional[str] = None


class DashboardSummary(BaseModel):
    total_posts: int
    posts_24h: int
    active_segments: int
    trending_topics: int
    emerging_count: int
    overall_sentiment: SentimentBreakdown
    platform_breakdown: List[PlatformStat]
    sentiment_timeline: List[TimePoint]
    demo_mode: bool


# ── Demographic segments ──────────────────────────────────────────────────────

class PersonaRead(BaseModel):
    id: int
    summary: Optional[str] = None
    interests: Optional[List[str]] = None
    reaction: Optional[Dict[str, Any]] = None
    influence_score: Optional[float] = None
    confidence: float
    evidence_json: Optional[Dict[str, Any]] = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class SegmentSummary(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    dominant_language: Optional[str] = None
    size_estimate: Optional[int] = None
    confidence: float
    evidence_count: int
    sentiment_profile: Optional[Dict[str, Any]] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SegmentDetail(SegmentSummary):
    geo_distribution: Optional[Dict[str, Any]] = None
    topic_prefs: Optional[Dict[str, Any]] = None
    activity_profile: Optional[Dict[str, Any]] = None
    persona: Optional[PersonaRead] = None

    model_config = {"from_attributes": True}


class SegmentList(BaseModel):
    items: List[SegmentSummary]
    total: int


# ── Trends ────────────────────────────────────────────────────────────────────

class TrendSummary(BaseModel):
    id: int
    name: str
    trend_score: float
    velocity: float
    acceleration: float
    is_emerging: bool
    platform_count: int
    platforms: Optional[List[str]] = None
    unique_users: int
    measured_at: datetime

    model_config = {"from_attributes": True}


class TrendList(BaseModel):
    items: List[TrendSummary]
    total: int


class TrendDetail(TrendSummary):
    volume_decay: float
    engagement: float
    community_spread: float
    sentiment_shift: float
    baseline_7d: float


# ── Sentiment ─────────────────────────────────────────────────────────────────

class SentimentAnalyzeRequest(BaseModel):
    text: str
    language: Optional[str] = None  # auto-detect if None


class SentimentResult(BaseModel):
    text: str
    language: str
    sentiment: str
    sentiment_score: float
    emotion: Optional[str] = None
    emotion_score: Optional[float] = None
    intensity: Optional[float] = None
    sarcasm_flag: Optional[bool] = None
    sarcasm_conf: Optional[float] = None
    epistemic_note: str = "model-inferred"


class SentimentTimeline(BaseModel):
    points: List[TimePoint]
    platform: Optional[str] = None
    language: Optional[str] = None


# ── Policy simulation ─────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    policy_text: str
    target_population: Optional[str] = "entire_population"
    question: Optional[str] = None
    use_local_llm: bool = False  # enrich narratives + executive brief via Ollama


class SegmentSimulationResponse(BaseModel):
    segment_id: int
    segment_name: str
    expected_sentiment: str
    sentiment_distribution: SentimentBreakdown
    intensity: float
    support_ratio: float
    likely_narratives: List[str]
    confidence: float
    evidence_count: int


class SimulationResult(BaseModel):
    id: str
    policy_text: str
    overall_sentiment: SentimentBreakdown
    overall_confidence: float
    analogues_used: List[str]
    topics_detected: List[str] = []
    segment_responses: List[SegmentSimulationResponse]
    influential_communities: List[str]
    potential_spread: str
    llm_brief: Optional[str] = None      # executive brief from local LLM
    disclaimer: str
    generated_at: datetime
    mode: str = "cloud"  # "cloud" | "local-llm"


# ── Ingestion / connector status ──────────────────────────────────────────────

class ConnectorStatusSchema(BaseModel):
    platform: str
    mode: str           # "mock" | "live"
    is_healthy: bool
    posts_ingested_total: int = 0
    last_ingested_at: Optional[datetime] = None
    error: Optional[str] = None


class PlatformIngestionStat(BaseModel):
    platform: str
    display_name: str
    total_posts: int
    nlp_processed: int
    nlp_coverage: float
    color: Optional[str] = None


class IngestionStats(BaseModel):
    total_posts: int
    nlp_processed: int
    nlp_coverage: float
    per_platform: List[PlatformIngestionStat]
    generated_at: datetime


class ModelStatus(BaseModel):
    name: str                          # e.g. "sentiment", "emotion", "irony", "embedding"
    loaded: bool
    error: Optional[str] = None
    use_real_nlp: bool = False


# ── Ollama / local LLM ────────────────────────────────────────────────────────

class OllamaStatus(BaseModel):
    available: bool
    base_url: str
    configured_model: str
    model_ready: bool
    available_models: List[str] = []


class OllamaTestRequest(BaseModel):
    prompt: Optional[str] = None


class OllamaTestResult(BaseModel):
    prompt: str
    response: str
    model: str


class PersonaRegenerateResult(BaseModel):
    segment_id: int
    persona_summary: str
    generated_by: str = "local-llm"

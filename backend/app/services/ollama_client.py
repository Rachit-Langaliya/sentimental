"""
Ollama local-LLM client — Phase 8.

Wraps the Ollama REST API for async persona generation, narrative enrichment,
and policy simulation briefing.  All calls degrade gracefully when Ollama is
unavailable — callers receive None and should fall back to deterministic output.

Model resolution order:
  settings.OLLAMA_MODEL  (default: llama3.2:3b)
"""
from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from app.core.config import settings

_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


# ── Low-level client ───────────────────────────────────────────────────────────

async def _post(path: str, payload: dict) -> Optional[dict]:
    """POST to Ollama API; return parsed JSON or None on any error."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


async def _get(path: str) -> Optional[dict]:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


# ── Public helpers ─────────────────────────────────────────────────────────────

async def is_available() -> bool:
    """Return True if Ollama is reachable."""
    result = await _get("/api/tags")
    return result is not None


async def list_models() -> list[str]:
    """Return names of locally available models."""
    result = await _get("/api/tags")
    if not result:
        return []
    return [m["name"] for m in result.get("models", [])]


async def pull_model(model: Optional[str] = None) -> bool:
    """Pull the configured model (non-streaming, best-effort)."""
    m = model or settings.OLLAMA_MODEL
    result = await _post("/api/pull", {"name": m, "stream": False})
    return result is not None


async def generate(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Optional[str]:
    """
    Raw text generation.  Returns the response string or None if Ollama is
    unavailable.  Temperature 0.3 keeps outputs focused; increase for creativity.
    """
    m = model or settings.OLLAMA_MODEL
    payload: dict = {
        "model": m,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.9,
        },
    }
    if system:
        payload["system"] = system

    result = await _post("/api/generate", payload)
    if result is None:
        return None
    return result.get("response", "").strip() or None


# ── High-level structured generators ──────────────────────────────────────────

async def generate_persona(segment: dict) -> Optional[str]:
    """
    Generate a 2-3 sentence persona summary for a demographic segment.

    segment dict keys expected: name, dominant_language, size_estimate,
      topic_prefs (dict), sentiment_profile (dict), geo_distribution (dict)
    """
    sp = segment.get("sentiment_profile") or {}
    pos = round((sp.get("positive") or 0) * 100)
    neu = round((sp.get("neutral") or 0) * 100)
    neg = round((sp.get("negative") or 0) * 100)

    tp = segment.get("topic_prefs") or {}
    top_topics = sorted(tp.items(), key=lambda x: -x[1])[:3]
    topic_str = ", ".join(t.replace("_", " ") for t, _ in top_topics) or "general policy"

    geo = segment.get("geo_distribution") or {}
    top_geo = list(geo.keys())[:3]
    geo_str = ", ".join(top_geo) or "India"

    prompt = (
        f"Segment name: {segment.get('name', 'Unknown segment')}\n"
        f"Primary language: {segment.get('dominant_language', 'English')}\n"
        f"Estimated size: {segment.get('size_estimate', 'unknown')} people\n"
        f"Top interests: {topic_str}\n"
        f"Sentiment breakdown: {pos}% positive, {neu}% neutral, {neg}% negative\n"
        f"Geographic focus: {geo_str}\n\n"
        f"Write a 2-3 sentence persona description for this citizen segment. "
        f"Describe who they are, what they care about most, and how they typically "
        f"react to government announcements. Be specific and grounded in Indian context. "
        f"Do NOT use bullet points. Output only the description."
    )

    system = (
        "You are a senior analyst at an Indian government policy intelligence centre. "
        "You write concise, accurate, and empathetic citizen persona profiles based on "
        "social media discourse data. Write in clear professional English."
    )

    return await generate(prompt, system=system, temperature=0.4, max_tokens=200)


async def generate_narratives(
    segment_name: str,
    policy_text: str,
    topics: list[str],
    expected_sentiment: str,
    segment_description: str = "",
) -> Optional[list[str]]:
    """
    Generate 4-5 likely narrative themes for a segment reacting to a policy.
    Returns a list of short phrase strings or None if Ollama unavailable.
    """
    topic_str = ", ".join(t.replace("_", " ") for t in topics) if topics else "general governance"

    prompt = (
        f"Policy/announcement: \"{policy_text}\"\n"
        f"Citizen segment: {segment_name}\n"
        f"Segment background: {segment_description or 'Indian citizens concerned about this policy'}\n"
        f"Related topics: {topic_str}\n"
        f"Predicted sentiment: {expected_sentiment}\n\n"
        f"List exactly 5 short narrative phrases (5-9 words each) that this citizen segment "
        f"would likely express about this policy on social media. "
        f"Each phrase should reflect an authentic concern, worry, or perspective. "
        f"Output exactly 5 phrases, one per line, no numbers, no bullets."
    )

    system = (
        "You are an Indian public opinion analyst. Generate realistic citizen narrative "
        "phrases that reflect authentic grassroots discourse in India. "
        "Phrases should sound like real social media posts, not formal policy language."
    )

    raw = await generate(prompt, system=system, temperature=0.5, max_tokens=150)
    if raw is None:
        return None

    lines = [ln.strip().lstrip("•-0123456789. ") for ln in raw.splitlines() if ln.strip()]
    lines = [ln for ln in lines if 3 <= len(ln.split()) <= 15][:5]
    return lines if lines else None


async def generate_policy_brief(
    policy_text: str,
    overall_sentiment: dict,
    potential_spread: str,
    overall_confidence: float,
    segment_summaries: list[str],
) -> Optional[str]:
    """
    Generate a 3-4 sentence executive intelligence brief for a simulation result.
    """
    pos = round((overall_sentiment.get("positive") or 0) * 100)
    neg = round((overall_sentiment.get("negative") or 0) * 100)
    neu = round(100 - pos - neg)
    segs = "\n".join(f"  - {s}" for s in segment_summaries[:6])

    prompt = (
        f"Policy: \"{policy_text}\"\n\n"
        f"Predicted public response:\n"
        f"  Overall: {pos}% positive, {neu}% neutral, {neg}% negative\n"
        f"  Confidence: {round(overall_confidence * 100)}%\n"
        f"  Expected spread: {potential_spread}\n\n"
        f"Key segment reactions:\n{segs}\n\n"
        f"Write a 3-4 sentence executive intelligence brief for a senior government official. "
        f"Identify the top 1-2 risk factors, which communities need targeted communication, "
        f"and one concrete messaging recommendation. Be direct and actionable. "
        f"Output only the brief, no heading."
    )

    system = (
        "You are writing an intelligence brief for a senior Indian government official. "
        "Be concise, direct, and policy-focused. Avoid generic statements. "
        "Focus on actionable intelligence."
    )

    return await generate(prompt, system=system, temperature=0.25, max_tokens=300)

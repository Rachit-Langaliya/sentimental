"""
Ollama management API — Phase 8.
Exposes Ollama health, model listing, warm-up, and quick test endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import CurrentUser
from app.core.config import settings
from app.schemas.schemas import OllamaStatus, OllamaTestRequest, OllamaTestResult

router = APIRouter()


@router.get("/status", response_model=OllamaStatus)
async def ollama_status(current_user: CurrentUser):
    """Check Ollama availability and list locally cached models."""
    from app.services import ollama_client
    available = await ollama_client.is_available()
    models = await ollama_client.list_models() if available else []
    configured_model = settings.OLLAMA_MODEL
    model_ready = any(
        configured_model in m or m.startswith(configured_model.split(":")[0])
        for m in models
    )
    return OllamaStatus(
        available=available,
        base_url=settings.OLLAMA_BASE_URL,
        configured_model=configured_model,
        model_ready=model_ready,
        available_models=models,
    )


@router.post("/warm")
async def warm_ollama(current_user: CurrentUser, background_tasks: BackgroundTasks):
    """
    Pull the configured model in the background.
    Safe to call multiple times — Ollama skips the pull if model is cached.
    """
    from app.services import ollama_client
    available = await ollama_client.is_available()
    if not available:
        raise HTTPException(status_code=503, detail="Ollama service not reachable at configured URL")

    async def _pull():
        await ollama_client.pull_model()

    background_tasks.add_task(_pull)
    return {"status": "pull_queued", "model": settings.OLLAMA_MODEL}


@router.post("/test", response_model=OllamaTestResult)
async def test_generation(body: OllamaTestRequest, current_user: CurrentUser):
    """
    Quick smoke-test: run a short generation and return the output.
    Useful to verify the model is loaded and responding correctly.
    """
    from app.services import ollama_client
    available = await ollama_client.is_available()
    if not available:
        raise HTTPException(status_code=503, detail="Ollama service not reachable")

    prompt = body.prompt or "In one sentence, explain what public opinion analysis is."
    output = await ollama_client.generate(
        prompt,
        temperature=0.3,
        max_tokens=100,
    )
    if output is None:
        raise HTTPException(status_code=503, detail="Model generation failed — model may not be pulled yet")

    return OllamaTestResult(
        prompt=prompt,
        response=output,
        model=settings.OLLAMA_MODEL,
    )

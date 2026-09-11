from fastapi import APIRouter

from app.api import auth, dashboard, ingest, segments, trends, sentiment, simulation

api_router = APIRouter()

api_router.include_router(auth.router,       prefix="/auth",       tags=["auth"])
api_router.include_router(dashboard.router,  prefix="/dashboard",  tags=["dashboard"])
api_router.include_router(segments.router,   prefix="/segments",   tags=["audience"])
api_router.include_router(trends.router,     prefix="/trends",     tags=["trends"])
api_router.include_router(sentiment.router,  prefix="/sentiment",  tags=["sentiment"])
api_router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
api_router.include_router(ingest.router,     prefix="/ingest",     tags=["ingestion"])

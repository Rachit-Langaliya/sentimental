from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_tables
from app.core.logging import configure_logging
from app.api.router import api_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(
        "starting_platform",
        version="1.0.0",
        demo_mode=settings.DEMO_MODE,
        env=settings.DATABASE_URL.split("@")[-1],  # log host only, not credentials
    )
    await create_db_tables()
    await _seed_initial_data()
    yield
    logger.info("platform_shutdown")


async def _seed_initial_data() -> None:
    from app.services.seed import seed_platforms, seed_admin_user

    await seed_platforms()
    await seed_admin_user()


app = FastAPI(
    title="SIH Intelligence Platform",
    description="AI-driven Social Media Analytics Framework for Public Policy Intelligence",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE, "version": "1.0.0"}

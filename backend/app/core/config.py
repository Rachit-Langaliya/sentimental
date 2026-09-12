from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=[".env", ".env.local"], extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://sih:sihpass@localhost:5432/sih_intelligence"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-change-me-in-production-needs-32-plus-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 h

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Feature flags
    DEMO_MODE: bool = True  # shows synthetic-data banner in UI

    # AI APIs
    ANTHROPIC_API_KEY: str = ""
    SARVAM_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Seed admin
    ADMIN_EMAIL: str = "admin@sih.gov.in"
    ADMIN_PASSWORD: str = "Admin@SIH2026"
    ADMIN_NAME: str = "Platform Administrator"

    # ── Phase 3 NLP ───────────────────────────────────────────────────────────
    USE_REAL_NLP: bool = False       # set True once ML deps installed & models cached
    HF_CACHE_DIR: str = "/app/.cache/huggingface"
    NLP_BATCH_SIZE: int = 32         # transformer inference batch size
    EMBEDDING_DIM: int = 384         # MiniLM output dimension

    # BERTopic model persistence
    TOPIC_MODEL_PATH: str = "/app/.cache/bertopic_model"
    TOPIC_MIN_DOCS: int = 30         # minimum docs before fitting BERTopic


settings = Settings()

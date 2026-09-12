# SIH Intelligence Platform
**AI-Driven Social Media Analytics Framework for Indian Public Policy**

> *Simulate before you announce* — understand citizen sentiment before policy goes public.

Built for **Smart India Hackathon 2026** | Problem Statement PS-1447 | Ministry of Electronics and Information Technology

---

## What it does

Government decision-makers face a critical gap: they cannot know how the public will react to a policy until it is already announced — and backlash is already spreading. This platform closes that gap.

**Core capabilities:**
- **Real-time ingestion** across Twitter/X, Facebook, Reddit, Instagram, YouTube, and news sites (mock + live connectors)
- **Multilingual NLP** — Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati + English, using transformer models fine-tuned on Indian social media
- **Topic modelling** with BERTopic + HDBSCAN, tracking 10+ policy topic clusters
- **Demographic segmentation** — clusters citizens by language, platform, topic interest, and sentiment profile
- **Policy Simulation Engine** — input a draft policy; get predicted support/opposition by segment, likely narratives, and confidence scores
- **Network analysis** — PageRank influence scoring, Louvain community detection, bridge actor identification
- **Local LLM** — on-device Ollama integration for persona generation and executive policy briefs (air-gapped deployment option)
- **Privacy-first** — DPDP Act 2023 compliant; author IDs pseudonymised, policy text never stored, 30-day TTL enforced

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Next.js 14)                                        │
│  Dashboard · Trends · Segments · Simulation · Network       │
└─────────────────┬───────────────────────────────────────────┘
                  │ REST / JSON
┌─────────────────▼───────────────────────────────────────────┐
│  FastAPI  (Python 3.11, async)                               │
│  /auth  /dashboard  /segments  /trends  /sentiment          │
│  /simulation  /network  /ingest  /ollama                     │
└──────┬──────────────┬───────────────────────────────────────┘
       │              │
┌──────▼──────┐  ┌────▼───────────────────────────────────────┐
│  PostgreSQL │  │  Celery Workers + Beat Scheduler            │
│  15+pgvector│  │  ├ Ingestion (every 2 min)                  │
│             │  │  ├ NLP batch (every 5 min)                  │
│  raw_posts  │  │  ├ Topic modelling (every 15 min)           │
│  post_nlp   │  │  ├ Trend recompute (every 10 min)           │
│  topics     │  │  ├ Segmentation (every 30 min)              │
│  trends     │  │  └ TTL cleanup (every hour)                 │
│  segments   │  └───────────────┬───────────────────────────┘
│  personas   │                  │
└─────────────┘  ┌───────────────▼─────────┐
                 │  Redis 7 (broker+cache)  │
                 └─────────────────────────┘
                 ┌─────────────────────────┐
                 │  Ollama (optional)       │
                 │  llama3.2:3b on-device  │
                 └─────────────────────────┘
```

---

## Quick Start (Docker — recommended)

### Prerequisites
- Docker Desktop 4.x+
- 4 GB RAM minimum (8 GB recommended for NLP models)

### 1. Clone and configure

```bash
git clone <repo>
cd TEAM007
cp .env.example .env
# Edit .env if needed — defaults work for local demo
```

### 2. Start all services

```bash
make demo
```

This runs: `docker compose up` (postgres + redis + backend + worker + beat + frontend) then seeds the database with ~2 000 realistic demo posts.

| Service      | URL                              |
|-------------|----------------------------------|
| Dashboard    | http://localhost:3000            |
| API docs     | http://localhost:8000/api/docs   |
| Backend      | http://localhost:8000            |

Default login: `admin@sih.gov.in` / `Admin@SIH2026`

### 3. (Optional) Enable Local LLM

```bash
make ollama
docker exec sih_ollama ollama pull llama3.2:3b
```

Then toggle "Local LLM Mode" in the Policy Simulation page for on-device narrative enrichment.

---

## Manual Setup (Development)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Set environment
cp ../.env.example .env
# Edit DATABASE_URL, REDIS_URL

# Run migrations and start
uvicorn app.main:app --reload --port 8000
```

In separate terminals:

```bash
# Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# Celery beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info
```

Seed demo data:

```bash
python -m app.scripts.seed_demo
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### Enable real NLP models (optional, ~2 GB download)

```bash
cd backend
pip install -r requirements-ml.txt
python -m app.scripts.download_models
# Then set USE_REAL_NLP=true in .env
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://sih:sihpass@localhost:5432/sih_intelligence` | Async PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `SECRET_KEY` | (dev default) | JWT signing secret — **change in production** |
| `USE_REAL_NLP` | `false` | Load transformer models (true = ~2 GB, false = rule-based fallback) |
| `DEMO_MODE` | `true` | Show demo banner in UI |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to use for local inference |
| `ADMIN_EMAIL` | `admin@sih.gov.in` | Auto-created admin account |
| `ADMIN_PASSWORD` | `Admin@SIH2026` | Admin password |

---

## Project Structure

```
TEAM007/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   │   ├── auth.py    simulation.py  network.py
│   │   │   ├── dashboard.py  segments.py  trends.py
│   │   │   ├── ingest.py  sentiment.py  ollama.py
│   │   │   └── router.py
│   │   ├── core/          # Config, DB session, auth deps
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   │   ├── nlp_pipeline.py       # Transformer inference
│   │   │   ├── topic_modeler.py      # BERTopic + keyword fallback
│   │   │   ├── trend_engine.py       # Composite trend scoring
│   │   │   ├── segmentation.py       # HDBSCAN demographic clustering
│   │   │   ├── simulation_engine.py  # Policy reaction prediction
│   │   │   ├── network_analyzer.py   # PageRank + Louvain
│   │   │   └── ollama_client.py      # Local LLM integration
│   │   ├── workers/       # Celery tasks + beat schedule
│   │   └── scripts/       # seed_demo.py, download_models.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/   # All authenticated pages
│   │   └── login/
│   ├── components/
│   ├── lib/               # api.ts, utils.ts, auth.ts
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## API Reference

Full interactive docs at **http://localhost:8000/api/docs** (Swagger UI) or `/api/redoc`.

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | JWT login |
| `GET` | `/api/v1/dashboard/summary` | KPI overview |
| `GET` | `/api/v1/trends/?limit=20` | Trending topics |
| `GET` | `/api/v1/segments/` | Demographic segments |
| `POST` | `/api/v1/simulation/run` | Policy reaction prediction |
| `GET` | `/api/v1/network/graph` | Force-directed influence graph |
| `GET` | `/api/v1/ollama/status` | Local LLM availability |
| `POST` | `/api/v1/segments/{id}/regenerate-persona` | LLM persona generation |

---

## Privacy & Compliance

| Mechanism | Implementation |
|-----------|---------------|
| **Author pseudonymisation** | `SHA-256(daily_salt + platform + user_id)` — reversible by no one |
| **Policy text privacy** | Only `SHA-256(policy_text)[:16]` stored in audit log |
| **Data retention** | Hard 30-day TTL on `raw_posts`, enforced by Celery beat |
| **Local-only mode** | Ollama runs fully offline — no data leaves the network |
| **Compliance** | Digital Personal Data Protection Act 2023 (DPDP Act) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector (embeddings), Redis 7 |
| Task queue | Celery 5 + Redis broker, persistent beat scheduler |
| NLP | sentence-transformers, XLM-RoBERTa, BERTopic, HDBSCAN |
| Local LLM | Ollama (llama3.2:3b default) |
| Deployment | Docker Compose, multi-service healthchecks |

---

## Makefile Commands

```bash
make demo          # Start all services + seed database
make up            # Start services only
make down          # Stop services
make seed          # Seed demo data
make logs          # Tail all logs
make ollama        # Start with local LLM sidecar
make build         # Rebuild Docker images
make psql          # Connect to database
```

---

## Team

Built for Smart India Hackathon 2026 — Team TEAM007  
Contact: agrawal123rishi@gmail.com

# SIH Intelligence Platform — Developer Makefile
# Usage: make <target>

.PHONY: help up down build seed logs ps restart clean

# ── Default: show help ────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  SIH Intelligence Platform"
	@echo "  ─────────────────────────"
	@echo "  make up        Start all core services (postgres, redis, backend, worker, beat, frontend)"
	@echo "  make seed      Populate the database with ~2 000 realistic demo posts"
	@echo "  make demo      up + seed (full one-command demo start)"
	@echo "  make down      Stop and remove containers"
	@echo "  make build     Rebuild Docker images"
	@echo "  make logs      Tail logs from all services"
	@echo "  make logs-api  Tail backend API logs only"
	@echo "  make ps        Show running containers"
	@echo "  make restart   Restart all services"
	@echo "  make clean     Remove containers, volumes, and images (destructive)"
	@echo "  make ollama    Start with local LLM (Ollama) sidecar"
	@echo ""

# ── Core targets ──────────────────────────────────────────────────────────────

up:
	docker compose up -d postgres redis backend worker beat frontend
	@echo ""
	@echo "  Services started:"
	@echo "    Frontend  → http://localhost:3000"
	@echo "    Backend   → http://localhost:8000"
	@echo "    API docs  → http://localhost:8000/docs"
	@echo ""

down:
	docker compose down

build:
	docker compose build --no-cache backend worker beat frontend

seed:
	@echo "Waiting for backend to be healthy before seeding..."
	docker compose --profile seed up seeder
	@echo ""
	@echo "  Demo data loaded. Refresh the dashboard."

demo: up
	@echo "Waiting 10s for services to stabilise..."
	@sleep 10
	$(MAKE) seed

logs:
	docker compose logs -f --tail=100

logs-api:
	docker compose logs -f --tail=100 backend

logs-worker:
	docker compose logs -f --tail=100 worker beat

ps:
	docker compose ps

restart:
	docker compose restart backend worker beat frontend

# ── Extended targets ──────────────────────────────────────────────────────────

ollama:
	docker compose --profile llm up -d
	@echo "Ollama running on http://localhost:11434"
	@echo "Pull a model: docker exec sih_ollama ollama pull llama3.2:3b"

# Destructive — removes volumes (all DB data)
clean:
	@echo "WARNING: This will delete all data including the database."
	@read -p "Press Enter to continue or Ctrl+C to abort..." confirm
	docker compose down -v --rmi local

# ── Development shortcuts ─────────────────────────────────────────────────────

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-worker:
	cd backend && celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

dev-beat:
	cd backend && celery -A app.workers.celery_app beat --loglevel=info

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ── Database helpers ──────────────────────────────────────────────────────────

migrate:
	docker compose exec backend python -m app.scripts.migrate_db

psql:
	docker compose exec postgres psql -U $${POSTGRES_USER:-sih} -d $${POSTGRES_DB:-sih_intelligence}

UV_CACHE_DIR ?= .uv-cache

.PHONY: run test lint typecheck check db-upgrade db-revision docker-up docker-prod-up

run:
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run uvicorn app.main:app --reload

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run pytest -q

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check .

typecheck:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run mypy app tests

check: lint typecheck test

db-upgrade:
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run alembic upgrade head

db-revision:
	@if [ -z "$(m)" ]; then echo "Usage: make db-revision m='message'"; exit 1; fi; \
	if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run alembic revision --autogenerate -m "$(m)"

docker-up:
	docker compose up --build

docker-prod-up:
	docker compose -f docker-compose.prod.yaml up -d --build

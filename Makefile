UV_CACHE_DIR ?= .uv-cache

.PHONY: run test lint typecheck check

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

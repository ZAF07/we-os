start:
	uv run uvicorn marketing_os.entrypoints.api.app:app --reload

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest -q

test:
	uv run pytest -q

# The Postgres suite starts its own throwaway container per run (testcontainers),
# so it needs Docker but no setup. Use this in CI.
test-postgres:
	MARKETING_OS_TEST_POSTGRES=1 uv run pytest -q

# A Postgres you can keep running, inspect with psql, and point the app at.
# Data lives in a tmpfs, so `db-down` leaves nothing behind.
db-up:
	docker compose up -d --wait
	uv run marketing-os init-db --dsn $(DB_ADMIN_DSN) --app-role marketing_os_app

db-down:
	docker compose down -v

db-shell:
	docker compose exec postgres psql -U marketing_os -d marketing_os

# Run the API against the compose database, as the non-superuser app role.
start-postgres: db-up
	MARKETING_OS_POSTGRES_DSN=$(DB_APP_DSN) uv run uvicorn marketing_os.entrypoints.api.app:app --reload

DB_ADMIN_DSN = postgresql://marketing_os:marketing_os@localhost:5435/marketing_os
DB_APP_DSN   = postgresql://marketing_os_app:marketing_os_app@localhost:5435/marketing_os

.PHONY: start check test test-postgres db-up db-down db-shell start-postgres

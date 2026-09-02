start:
	uv run uvicorn marketing_os.entrypoints.api.app:app --reload

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest -q

test:
	uv run pytest -q

# The Postgres suite needs Docker: it starts a real server, applies the schema,
# and runs the DocumentStore conformance assertions plus row-level security,
# the shared run claim, and checkpoint durability against it.
test-postgres:
	MARKETING_OS_TEST_POSTGRES=1 uv run pytest -q

.PHONY: start check test test-postgres

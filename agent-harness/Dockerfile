# The engine, for the end-to-end test stack.
#
# Test-only: it installs dev extras and mounts the repo's governance markdown,
# because the engine reads agent specs, guardrails and templates from the repo
# root at runtime (ADR-0003). Not a production image.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies resolve from the manifest alone, so this layer survives edits to
# the source underneath it.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --extra postgres

COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --extra postgres

ENV PATH="/app/.venv/bin:$PATH"

# The repo root the engine reads code-shipped material from; the compose file
# mounts the working tree there.
ENV MARKETING_OS_ROOT=/repo

EXPOSE 8000

CMD ["uvicorn", "marketing_os.entrypoints.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

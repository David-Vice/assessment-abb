FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:0.9.14 /uv /usr/local/bin/uv
WORKDIR /app

# All workspace member manifests — uv resolves the whole workspace before syncing.
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/
COPY libs/rag/pyproject.toml libs/rag/
COPY apps/ingestion/pyproject.toml apps/ingestion/
COPY apps/chat/pyproject.toml apps/chat/
COPY apps/analytics/pyproject.toml apps/analytics/
COPY apps/scraper/pyproject.toml apps/scraper/

# Source for the target package + its workspace deps.
COPY packages/contracts/ packages/contracts/
COPY libs/rag/ libs/rag/
COPY apps/analytics/ apps/analytics/

RUN uv sync --frozen --package abb-analytics --no-dev

RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8003
CMD ["uv", "run", "--no-sync", "--no-dev", "uvicorn", "abb_analytics.main:app", "--host", "0.0.0.0", "--port", "8003"]

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

# Workspace metadata for resolution
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/
COPY libs/rag/pyproject.toml libs/rag/
COPY apps/ingestion/pyproject.toml apps/ingestion/

# Source
COPY packages/contracts/ packages/contracts/
COPY libs/rag/ libs/rag/
COPY apps/ingestion/ apps/ingestion/

RUN uv sync --frozen --package abb-ingestion --no-dev

EXPOSE 8001
RUN useradd -m appuser
USER appuser
CMD ["uv", "run", "--no-dev", "uvicorn", "abb_ingestion.main:app", "--host", "0.0.0.0", "--port", "8001"]

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/
COPY libs/rag/pyproject.toml libs/rag/
COPY apps/analytics/pyproject.toml apps/analytics/

COPY packages/contracts/ packages/contracts/
COPY libs/rag/ libs/rag/
COPY apps/analytics/ apps/analytics/

RUN uv sync --frozen --package abb-analytics --no-dev

EXPOSE 8003
RUN useradd -m appuser
USER appuser
CMD ["uv", "run", "--no-dev", "uvicorn", "abb_analytics.main:app", "--host", "0.0.0.0", "--port", "8003"]

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/
COPY libs/rag/pyproject.toml libs/rag/
COPY apps/chat/pyproject.toml apps/chat/

COPY packages/contracts/ packages/contracts/
COPY libs/rag/ libs/rag/
COPY apps/chat/ apps/chat/

RUN uv sync --frozen --package abb-chat --no-dev

EXPOSE 8002
RUN useradd -m appuser
USER appuser
CMD ["uv", "run", "--no-dev", "uvicorn", "abb_chat.main:app", "--host", "0.0.0.0", "--port", "8002"]

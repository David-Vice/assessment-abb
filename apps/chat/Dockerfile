FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Fixed, in-image HF cache so build and runtime share one path and the baked
# reranker weights are found without a network fetch.
ENV HF_HOME=/app/.cache/huggingface
COPY --from=ghcr.io/astral-sh/uv:0.9.14 /uv /usr/local/bin/uv

# Run as a non-root user owning /app from the start, so installs write
# already-owned files — avoids a slow recursive chown over the venv + model.
RUN useradd -m appuser
WORKDIR /app
RUN chown appuser:appuser /app
USER appuser

# All workspace member manifests — uv resolves the whole workspace before syncing.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
COPY --chown=appuser:appuser packages/contracts/pyproject.toml packages/contracts/
COPY --chown=appuser:appuser libs/rag/pyproject.toml libs/rag/
COPY --chown=appuser:appuser apps/ingestion/pyproject.toml apps/ingestion/
COPY --chown=appuser:appuser apps/chat/pyproject.toml apps/chat/
COPY --chown=appuser:appuser apps/analytics/pyproject.toml apps/analytics/
COPY --chown=appuser:appuser apps/scraper/pyproject.toml apps/scraper/

# INSTALL_RERANK=true pulls the local BGE reranker (torch) via the `rerank`
# extra; default false keeps the image lean (hybrid-only retrieval).
ARG INSTALL_RERANK=false

# Phase 1 — third-party dependencies only (no workspace source needed yet).
# This heavy layer (incl. torch when reranking) is keyed on uv.lock + manifests,
# so editing app source never re-installs it.
RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        uv sync --frozen --package abb-chat --extra rerank --no-install-workspace --no-dev; \
    else \
        uv sync --frozen --package abb-chat --no-install-workspace --no-dev; \
    fi

# Phase 2 — pre-bake the reranker weights into the image (only when installed).
# Placed before the app-source COPY so code edits don't invalidate it: the model
# downloads once (first build / dep change), not on every rebuild or first query.
RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        .venv/bin/python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"; \
    fi

# Phase 3 — workspace source, then install the editable members (fast: deps and
# model are already present, nothing re-downloads).
COPY --chown=appuser:appuser packages/contracts/ packages/contracts/
COPY --chown=appuser:appuser libs/rag/ libs/rag/
COPY --chown=appuser:appuser apps/chat/ apps/chat/
RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        uv sync --frozen --package abb-chat --extra rerank --no-dev; \
    else \
        uv sync --frozen --package abb-chat --no-dev; \
    fi

EXPOSE 8002
# Exec the server binary directly so it is PID 1 and receives SIGTERM for a fast
# graceful shutdown (no `uv run` wrapper swallowing the signal).
CMD ["/app/.venv/bin/uvicorn", "abb_chat.main:app", "--host", "0.0.0.0", "--port", "8002"]

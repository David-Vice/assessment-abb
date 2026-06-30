FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENV HF_HOME=/app/.cache/huggingface
COPY --from=ghcr.io/astral-sh/uv:0.9.14 /uv /usr/local/bin/uv

RUN useradd -m appuser
WORKDIR /app
RUN chown appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock ./
COPY --chown=appuser:appuser packages/contracts/pyproject.toml packages/contracts/
COPY --chown=appuser:appuser libs/rag/pyproject.toml libs/rag/
COPY --chown=appuser:appuser apps/chat/pyproject.toml apps/chat/
COPY --chown=appuser:appuser eval/pyproject.toml eval/

# Match chat image: bake reranker when INSTALL_RERANK=true (same as prod).
ARG INSTALL_RERANK=false

RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        uv sync --frozen --package abb-eval --package abb-chat --extra rerank --no-install-workspace --no-dev; \
    else \
        uv sync --frozen --package abb-eval --no-install-workspace --no-dev; \
    fi

RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        .venv/bin/python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"; \
    fi

COPY --chown=appuser:appuser packages/contracts/ packages/contracts/
COPY --chown=appuser:appuser libs/rag/ libs/rag/
COPY --chown=appuser:appuser apps/chat/ apps/chat/
COPY --chown=appuser:appuser eval/ eval/
COPY --chown=appuser:appuser corpus.sample.json corpus.sample.json

RUN if [ "$INSTALL_RERANK" = "true" ]; then \
        uv sync --frozen --package abb-eval --package abb-chat --extra rerank --no-dev; \
    else \
        uv sync --frozen --package abb-eval --no-dev; \
    fi

ENTRYPOINT ["/app/.venv/bin/abb-eval"]
CMD ["--help"]

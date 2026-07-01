# Thin eval layer on the chat image — reuses torch, reranker, and abb-chat
# (avoids a 30+ minute duplicate download). Build chat first:
#   docker compose build chat
#   docker compose --profile eval build eval
ARG CHAT_IMAGE=abb-rag-chat
FROM ${CHAT_IMAGE}

USER appuser
WORKDIR /app

COPY --chown=appuser:appuser pyproject.toml uv.lock ./
COPY --chown=appuser:appuser eval/pyproject.toml eval/
COPY --chown=appuser:appuser eval/ eval/
COPY --chown=appuser:appuser corpus.sample.json corpus.sample.json

# Only installs abb-eval + RAGAS; keep abb-chat[rerank] from the base image.
RUN uv sync --frozen --package abb-eval --package abb-chat --extra rerank --no-dev

ENTRYPOINT ["/app/.venv/bin/abb-eval"]
CMD ["--help"]

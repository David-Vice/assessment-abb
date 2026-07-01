#!/usr/bin/env bash
# Prod-faithful eval: reuses the chat image (rerank + .env). Builds eval layer only.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose build chat
docker compose --profile eval build eval

# MSYS_NO_PATHCONV: Git Bash on Windows mangles /app/... before it reaches the container.
export MSYS_NO_PATHCONV=1
docker compose --profile eval run --rm eval \
  --corpus corpus.sample.json \
  --output-dir eval/results \
  "$@"

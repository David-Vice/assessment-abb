#!/usr/bin/env bash
# Prod-faithful eval: same rerank stack + .env as the chat container.
# Writes reports to eval/results/ on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile eval run --rm eval \
  --corpus /app/corpus.sample.json \
  --output-dir /app/eval/results \
  "$@"

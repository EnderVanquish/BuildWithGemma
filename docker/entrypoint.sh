#!/bin/sh
# Runtime entrypoint: starts Ollama and the Argus dashboard in the same container,
# so the resource caps constrain the whole system (inference included), not just the
# app code. The model is already baked into the image (see pull_model.sh), so nothing
# here requires network access — which is what makes the offline proof genuine.
set -e

ollama serve &

for i in $(seq 1 60); do
  if curl -sf http://localhost:11434/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[argus] ollama ready, model: $MODEL_NAME"

# In-container Ollama is local; override the dev default (which points at the port
# the container publishes to the host). Note this is ARGUS_OLLAMA_URL, not
# OLLAMA_HOST — the latter is what `ollama serve` binds to, set in the Dockerfile.
export ARGUS_OLLAMA_URL="${ARGUS_OLLAMA_URL:-http://localhost:11434}"
export PYTHONPATH=/app/src

exec python -u /app/src/dashboard/backend/app.py

#!/bin/sh
# Runtime entrypoint. The model is already baked into the image (see pull_model.sh),
# so nothing here requires network access.
set -e

ollama serve &

for i in $(seq 1 30); do
  if curl -sf http://localhost:11434/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Ollama ready with model $MODEL_NAME baked in."

# Placeholder until the reasoning loop + dashboard backend exist (M2/M3).
exec tail -f /dev/null

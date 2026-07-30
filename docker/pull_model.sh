#!/bin/sh
# Build-time only: starts Ollama, pulls the model into the image layer, then stops.
# This means the model ships baked into the image and the container never needs
# network access at runtime (see resource_caps.md).
set -e

ollama serve &
SERVER_PID=$!

for i in $(seq 1 30); do
  if curl -sf http://localhost:11434/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

ollama pull "$MODEL_NAME"

kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true

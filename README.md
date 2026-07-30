# Argus — Privacy-First Local Security Camera Reasoner

A local security-camera reasoning assistant built for the Gemma 4 Hackathon Sprint
(AI off the Grid track). Frames from a camera feed are periodically sent to a locally
running Gemma model (via Ollama) along with a rolling history of recent observations, so it
can reason about whether activity is routine or unusual over time — not just detect objects
in a single frame. Raw frames never leave the device; only text observations persist.

The whole stack (Ollama + Gemma model + app logic + dashboard) runs inside a single Docker
container with hard resource caps simulating basic security-camera-class edge hardware, with
a live dashboard proving RAM/CPU/tokens-per-sec usage and zero outbound network traffic.

See [project-context.md](project-context.md) for the full pitch, differentiators, and design
decisions, and [CLAUDE.md](CLAUDE.md) for repo/dev operational guidance.

## Quickstart (local dev)
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Docker build/run instructions will be added once the all-in-one image (`docker/Dockerfile`)
is built.

## Status
Reasoning pipeline (`src/reasoning/`, `src/capture/`) and the dashboard skeleton
(`src/dashboard/static/`, branded as Argus) are built; the Flask/SSE backend, feature
work (ask-a-question, severity sparkline), and the Docker port/resource-cap validation
are still in progress. See `project-context.md`'s "Milestones" section for current status.

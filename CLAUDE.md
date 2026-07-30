# CLAUDE.md

Operational guidance for working in this repo. For the project idea, hackathon constraints,
and design decisions, see `project-context.md` — this file only covers what that one doesn't.

## Directory map
```
docker/       Dockerfile, entrypoint, resource cap docs (all-in-one: Python + Ollama + Gemma)
src/capture/    Frame source abstraction (video file / live feed)
src/reasoning/  Ollama client, prompt templates, rolling history buffer, output schema
src/monitor/    RAM/CPU stats (psutil), network traffic check
src/dashboard/  backend/ (Flask app) + static/ (HTML/JS/CSS dashboard page)
demo/clips/     Scripted video snippets used for the recorded demo
demo/scenarios/ History-injection scripts for the temporal-reasoning proof
```
See the approved plan at project-context.md's milestone breakdown for what goes in each
folder as it's built out.

## Local dev setup
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
`requirements.txt` is the single source of truth for dependencies — used for both local dev
and the Docker image. Install cleanly into a fresh venv rather than the system Python.

## Docker
The whole stack (Ollama + Gemma model + app logic + dashboard backend) runs inside one
resource-capped container to genuinely simulate basic security-camera-class edge hardware —
not just the app code. See `docker/resource_caps.md` for the chosen `--memory`/`--cpus`
values and their rationale once picked.

**Hard rule**: every component (reasoning loop, dashboard backend, any future service) must
be designed assuming it runs under those resource caps. Don't build against unconstrained
local dev resources and bolt the caps on at the end.

## Git / GitHub Desktop
This repo is tracked via GitHub Desktop and pushes to
`https://github.com/EnderVanquish/BuildWithGemma`. Don't run `git push`, rebase, or commit
via CLI on this user's behalf — leave commits/pushes to GitHub Desktop (or ask first if a
CLI commit is genuinely needed).

## Hard rules
- **Never refactor or delete files/directories without asking permission first.**
- Keep `requirements.txt` in sync with actual imports — install cleanly, don't hand-patch
  environments.

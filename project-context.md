# Project Context: Argus — Privacy-First Local Security Camera Reasoner

**Product name: Argus** (decided during the dashboard UI pass — used in the dashboard
title/header, README, and should be used in the Kaggle writeup title going forward).

## Event
Gemma 4 Hackathon Sprint (GDG on Campus VIT Chennai), 1-day, ~8-10 hour build.
Track: **AI off the Grid** (edge computing — lightweight Gemma models running locally on
mobile/web/IoT/desktop, fast/low-latency/privacy-first, no cloud dependency).

Judging rubric: Gemma Integration (30%), Innovation & Impact (30%), Functionality (20%),
Presentation & Writeup (20%). Submission needs a Kaggle Writeup (<=1500 words), a public
code repo, and a live demo (or clonable notebook).

## The idea
A local security-camera reasoning assistant. Frames come in from a camera feed
(video file for demo reliability, or a live WiFi camera stream on the local network —
see "Camera feed" below). Every N seconds (not continuous streaming — deliberately
periodic, framed as a design choice for edge efficiency), a frame is sent to a locally
running Gemma model (`gemma4:e2b`, multimodal, via Ollama) along with a short rolling
history of recent observations.

Gemma's job is NOT simple object/person detection (a bounding-box classifier could do
that). Its job is **contextual reasoning over time**: deciding whether what's happening
is routine or unusual given the situation and history — e.g. "delivery person at door
for 8 seconds, placed a package, left" (normal) vs. "unfamiliar person lingered near
the door for 3 minutes without approaching, returned 3 times in 10 minutes" (flag).
Output is structured (see `src/reasoning/schema.py`): observation, unusual (bool),
severity, and — importantly — the reasoning behind the judgment (not just a verdict),
since transparency/explainability is a deliberate part of the pitch (see "Known
weaknesses" below).

Core technical/architectural decision: the reasoning loop + dashboard back end run
inside a Docker container with hard resource caps (`--memory=6g --cpus=2`) to simulate
real IoT/edge hardware constraints (Jetson Nano 4GB class — see `docker/resource_caps.md`),
with a live on-screen dashboard showing RAM/CPU/tokens-per-sec during the demo, and a
network monitor showing zero *outbound* traffic (network killed) to prove the offline/
privacy claim concretely rather than asserting it. **Build order was revised mid-build**:
Docker packaging is validated last, not developed against continuously — see "Build
order" below.

## Why this idea (the actual differentiator)
Commercial smart cameras (Ring, Nest, Arlo) already do "unusual activity" detection —
but they stream raw footage to company servers to do it. This project's whole point is
that raw frames never leave the device — only text observations/alerts persist, frames
are discarded immediately after reasoning. The pitch must foreground this privacy
contrast explicitly, not just describe "AI camera that detects weird stuff" (that reads
as a worse clone of an existing product). "Your footage never leaves this room" is the
one-sentence hook.

## Known weaknesses / already-discussed mitigations (keep these in mind while building)
- **Latency**: multimodal inference on a CPU-capped container may be slow (needs testing
  early — this determines demo format: periodic sampling, not real-time streaming, and
  the pitch should explicitly frame periodic checking as a deliberate edge-efficiency
  design choice, not a limitation). Tokens/sec on the dashboard is the concrete evidence
  for this, not a vanity metric — it's what justifies the sampling-interval choice.
- **Risk of just being frame-captioning, not real reasoning**: the demo must explicitly
  prove temporal reasoning matters — e.g. showing the same frame produce a different
  verdict depending on injected/fabricated history, side by side. This lives as a
  standalone script (`demo/scenarios/same_frame_different_history.py`), not a dashboard
  UI feature — see "Feature scope" below for why.
- **False positives/negatives are highly visible in a live demo** given the "security"
  framing raises stakes. Mitigation: don't pitch "flags suspicious activity accurately" —
  pitch "explains its reasoning so a human can decide" (safer, true claim, also ties into
  interpretability which is more of an AI Shield concept but strengthens this pitch too).
- **Crowded idea space**: plenty of teams will do "camera + AI." Differentiation must come
  from (a) the privacy/local-only proof (Docker cap + live network monitor) and (b) a
  demo scenario requiring genuine contextual judgment a commercial camera's classifier
  can't do (e.g. combining "not a recognized household member" + "unusual hour" +
  "did not approach the door," not just "person detected").
- Considered AI Shield as an alternate track (since the transparent-reasoning angle
  maps well there) but decided to stay in AI off the Grid, since the resource-capped/
  offline proof is the strongest differentiator already built, and the writeup's
  Innovation & Impact argument should lean on the contextual-reasoning-over-time angle,
  not privacy alone.

## Stack (as built)
- **Model**: `gemma4:e2b` (multimodal, ~7.2GB via `ollama pull`) via Ollama.
- **Reasoning pipeline** (`src/reasoning/`): `schema.py` (pydantic `ObservationRecord`:
  timestamp/observation/unusual/severity/reasoning), `history.py` (`RollingHistory`,
  deque-backed, default last 10), `prompts.py` (system prompt + history formatting,
  forces strict JSON), `client.py` (`reason_about_frame()` — encodes frame as JPEG,
  calls Ollama with `format="json"`, returns a parsed `ObservationRecord`).
- **Capture** (`src/capture/`): `FrameSource` ABC, `VideoFileSource` (loops a video
  file), `LiveStreamSource` (RTSP/HTTP URL — e.g. the "IP Webcam" Android app over LAN).
- **Dashboard**: vanilla HTML + Tailwind (`@tailwindcss/browser@4`) + daisyUI, both
  **vendored locally** under `src/dashboard/static/vendor/` rather than loaded from a
  CDN — see "Frontend stack" decision below for why. Backend will be Flask + SSE
  (`src/dashboard/backend/` not yet implemented).
- **Container**: Docker, all-in-one image (Python + Ollama + baked-in model), hard caps
  `--memory=6g --cpus=2` — see `docker/resource_caps.md`.

## Decisions made (2026-07-30 clarification round)
- **Submission format**: the hackathon submission is reviewed asynchronously — a Kaggle
  Writeup (<=1500 words), a public code repo, and a demo video/notebook. There is no live
  pitch/Q&A. This means we optimize for a clean recorded take rather than for live-demo
  robustness — scripted/looped clips and retakes are fine if the final video looks good.
- **Camera feed**: build genuine live-feed capability over the local WiFi network (e.g.
  the "IP Webcam" Android app, which broadcasts directly on the LAN with no cloud
  account/relay — chosen over apps whose pairing routes through a cloud service, which
  would violate the offline claim). LAN traffic between camera and reasoner does **not**
  conflict with the track's "no cloud dependency" theme — it never leaves the premises.
  The network monitor must distinguish LAN traffic (expected, shown as fine) from
  outbound/WAN traffic (the thing actually being proven zero). The actual recorded demo
  will still primarily use a pre-recorded video snippet for reliability, with the live
  WiFi stream as a bonus moment.
- **Containerization is the organizing constraint for the reasoning/dashboard backend,
  not the dev loop.** See "Build order" below — this was refined mid-build.
- **Resource caps**: `--memory=6g --cpus=2`, grounded in the Jetson Nano 4GB board
  (quad-core Cortex-A57 @ 1.43GHz, 4GB RAM) as the reference edge-device class, with
  headroom added above the Nano's literal 4GB for `gemma4:e2b` + Ollama overhead to
  actually fit. Full rationale and research notes in `docker/resource_caps.md`.
- **Identity/familiarity concept**: decided — a lightweight text config (e.g. "mail
  carrier visits weekdays 2-4pm"; no household members currently listed) fed into every
  prompt as extra context, **not** face recognition. Keeps the privacy-first framing and
  avoids turning the system into a classifier. Not yet implemented.

## Validated findings (2026-07-30, during M1/M2)
- **Gemma 4 vision is broken on native Windows Ollama, and works fine on Linux.**
  Confirmed empirically: on Windows (Ollama 0.32.5), `gemma4:e2b` reports `vision` in its
  capabilities and accepts images without error, but the model's own reasoning trace states
  no image was received; it either says "please provide an image" or hallucinates an
  unrelated description. Reproduced via the Python client, the CLI, and the raw HTTP API,
  so it is not our code. Matches open upstream issues ollama/ollama#16532, #16597, #16874;
  the fix (PR #16879) is unmerged as of this date. **Inside the Linux container the same
  model correctly describes the same image**, so the reasoning pipeline must be developed
  and demoed via the container, not native Windows.
- **`gemma3n:e2b` is NOT multimodal** — `ollama show` lists only `completion` (no vision).
  An early Dockerfile default accidentally baked this model in; it cannot do frame
  reasoning at all and is not a usable fallback. `docker/Dockerfile`'s `MODEL_NAME` arg was
  corrected to `gemma4:e2b` and moved below the pip layer so future model-tag changes don't
  invalidate the apt/pip cache.
- **`psutil.virtual_memory()` reports HOST memory even inside a container** (it reads
  non-namespaced /proc/meminfo), which would have made the dashboard show e.g. "15.4 / 6.0
  GB" and misrepresent the project's central resource-cap claim. `src/monitor/resources.py`
  now reads cgroup v2/v1 (`memory.current`/`memory.max`) instead, falling back to psutil
  only outside a container and labelling which source is in use so the UI never implies a
  cap that isn't enforced. Verified inside the capped container: reports `0.46 / 6.0 GB,
  source=cgroup`, and `memory.max` reads exactly 6442450944 bytes = the `--memory=6g` cap.
- **Ask-a-question works end-to-end** against real Gemma (text-only, so unaffected by the
  vision bug). Given the seeded log it correctly answered "Did anything concerning happen?"
  with the specific unusual event, its timestamp, and its severity.
- **CPU-only inference latency is significant** (tens of seconds per multimodal call under
  the cap), which supports the periodic-sampling design choice rather than undermining it —
  this is the number the dashboard's tokens/sec tile exists to make concrete.
- **The end-to-end reasoning loop works.** Running `src/reasoning/loop.py` against the porch
  CCTV clip produced a real structured observation ("An empty room with white walls, a white
  door… a metal chair and a woven basket visible", `unusual=False`, `severity=none`) with the
  reasoning correctly citing the absence of prior history, at 3.28 tok/s.
- **Full-resolution CCTV frames must be downscaled.** The clip's frames are 2732x1440
  (3.93 MP), above Gemma 4's ~2.6 MP input limit. `src/reasoning/client.py:downscale()` now
  caps the longest side at `MAX_FRAME_DIM` (768px → ~0.31 MP). This is both a correctness fix
  and a legitimate edge optimisation — a person at a door is perfectly legible at that size,
  and it cuts memory and inference time.
- **Zero swap is fatal, and it was a self-inflicted bug.** `docker update --memory=Xg
  --memory-swap=Xg` sets swap to *zero*, which SIGKILLed `llama-server` on every inference
  (39 `oom_kill` events) even while the container sat well below its limit. Docker's default
  when only `--memory` is given is 2x (i.e. swap allowed), which is why it worked before the
  "increase". Caps are now `--memory=6g --memory-swap=12g --cpus=2`; see
  `docker/resource_caps.md`.
- **This machine is the binding constraint, not the design.** Docker's VM is 7.611 GiB and the
  Windows host usually has ~1 GiB free, so the container cannot grow beyond ~6GB. At 6GB it
  runs at ~97% memory with swap thrashing during inference — functional but with no headroom,
  and that thrashing is a major contributor to the ~3.3 tok/s figure. Smaller Gemma 4 variants
  (`gemma4:e2b-it-qat`, or the community `gemma4-nano` Q3_K_S at ~3.1GB) are the obvious lever
  if speed becomes a blocker, and would keep the project on Gemma 4.

## Frame-source config
The reasoning loop reads its source from env vars (`src/config.py`, `.env` supported):
`FRAME_SOURCE` (video path, or an RTSP/HTTP URL), `SOURCE_KIND` (`file` | `stream`),
`OLLAMA_HOST`, `SAMPLE_INTERVAL_SECONDS`, `MAX_FRAME_DIM`. With `FRAME_SOURCE` unset the
backend still serves stats and the log, but the reasoning loop stays off.

## Demo footage status
`demo/clips/` holds a 50s 720p porch-theft CCTV clip (YouTube rip from a security installer's
channel). **Fine for local development, but not safe to republish** in the demo video, the
Kaggle writeup, or the public repo — no rights to the footage or the people in it. Same applies
to `demo/scenarios/placeholder/image.png` and `src/dashboard/static/placeholder_frame.png`,
which look like vendor marketing stills. Public-facing material should use Pexels footage
(free, model-released, commercial use) or self-shot video. Note also that the clip's opening
frames are an indoor/title scene rather than the porch, so the interesting moment is later in
the timeline.

## Build order (revised mid-build)
Originally planned as Docker-first (Docker was M1, before the reasoning pipeline). In
practice, the model bake-in step inside the Docker build was network-bound and slow
(large model layer, constrained connection), which made it a poor thing to iterate
against for reasoning-pipeline development. Revised order: **Docker is now the last
milestone (M5), not the first** — the reasoning pipeline and dashboard are built and
validated end-to-end against a natively installed Ollama (fast local iteration, no
container rebuild per change), and only ported into the Docker image afterward as a
packaging/validation step. Docker remains the tool for the final resource-cap proof
(it's the simplest way to get genuine OS-enforced limits — cgroups under the hood —
rather than fragile self-imposed throttling), it's just no longer the day's dev loop.
See "Milestones" below for the current M0-M6 breakdown.

## Frontend stack decision
Considered React + shadcn/ui + Radix (closest to a polished, non-generic-AI look) but
rejected for a one-day build: shadcn is React + Tailwind + Radix under the hood, meaning
a real npm/Vite build step and more scaffolding than the timeline supports, for a page
with no forms/dialogs/dropdowns that would actually benefit from Radix's primitives.
Landed on **vanilla HTML + Tailwind (browser) + daisyUI** instead — component classes
(`card`, `badge`, `progress`) give most of the visual polish without a framework. Both
libraries are **vendored locally** (`src/dashboard/static/vendor/`) rather than loaded
from jsdelivr's CDN at runtime — a live CDN dependency would break (or silently rely on
browser cache) during the exact demo moment the network gets killed to prove the
zero-outbound claim, which would undercut the proof it's supposed to be part of.
Live updates use **SSE**, not polling, chosen so RAM/CPU numbers can update faster than
the reasoning loop's own sampling cadence.

## Feature scope (decided)
- **Same-frame-different-history proof**: stays a standalone script
  (`demo/scenarios/same_frame_different_history.py`), not a dashboard UI toggle. In real
  operation every frame only ever has one true history, so the side-by-side comparison
  is a manufactured demo/proof tool, not a live feature — no need to duplicate it in the UI.
- **Added: ask-a-question over the log** — a text input on the dashboard where a
  question like "was anyone at the door after 10pm?" is answered by Gemma using the
  stored `ObservationRecord` history as context (a lightweight RAG-style path, reusing
  the same model). Adds a second distinct Gemma capability beyond per-frame judgment and
  makes the explainability pitch interactive rather than passive. Not yet implemented.
- **Added: severity-over-time sparkline** in the history panel, replacing/supplementing
  the plain list — a real small chart following the dataviz status-color rules already
  used for severity badges. Not yet implemented.
- **Explicitly skipped**: SMS/webhook alerting (pulls in an external service, conflicts
  with the offline pitch unless purely a local browser notification — not worth the
  scope); broader historical analytics dashboards (not enough real data in a short demo
  to justify it; would read as padding).

## Milestones (restructured — Docker removed from M1, ask-a-question/sparkline/UI
finalization made explicit)
- **M0 — Repo scaffolding**: done, committed locally (`9a22839`).
- **M1 — Native reasoning pipeline** (no Docker involved at all): capture abstraction,
  schema, history, prompts, and Ollama client all written (`src/capture/`,
  `src/reasoning/`). Native `gemma4:e2b` pull in progress via the natively installed
  Ollama. Next: smoke-test `reason_about_frame` end-to-end against
  `demo/scenarios/same_frame_different_history.py` once the pull finishes. This
  milestone is done when the pipeline produces correct, differing verdicts for the same
  frame under the two fabricated histories.
- **M2 — Dashboard backend + real data wiring**: build the Flask + SSE backend
  (`src/dashboard/backend/`, currently empty), replace the placeholder `setInterval`
  loop in `src/dashboard/static/app.js` with real data from the M1 pipeline (RAM/CPU via
  `psutil`, tokens/sec timed around Ollama calls, real observations instead of the
  sample array).
- **M3 — Feature additions**: ask-a-question over the log (mini RAG endpoint + UI input,
  reuses the Ollama client against stored `ObservationRecord` history instead of a
  frame), severity-over-time sparkline in the history panel (replacing/supplementing the
  plain list), and the household/context registry (text config fed into every prompt).
- **M4 — UI finalization**: once M2/M3 are wired up, a polish pass on the daisyUI
  dashboard — visual QA of the real (non-placeholder) data states, responsive check,
  dark/light theme toggle behavior, empty/loading states (e.g. before the first
  observation exists).
- **M5 — Port to Docker + verify resource caps**: only after M1-M4 are proven correct
  natively. Bake the validated pipeline + dashboard into the all-in-one image
  (`docker/Dockerfile`, already written and previously confirmed buildable up through
  the Ollama install step), resume the model bake-in build, and confirm it actually
  loads and runs within `--memory=6g --cpus=2` without OOM. Also implement the network
  monitor's LAN-vs-WAN traffic distinction here, since it only matters once there's a
  real container network boundary to monitor.
- **M6 — Demo scenario assets + recording, writeup, polish**: replace the synthetic
  placeholder frame in `demo/scenarios/` with a real captured frame/video, record the
  demo (network-kill moment included), write the Kaggle writeup, final repo cleanup.

## Not yet decided / open questions
- Exact camera feed source for the final recorded demo clip
- Frame sampling frequency (depends on latency testing, now unblocked by native Ollama)
- Whether/how to reconcile the two different model manifest sizes seen so far (Docker's
  pull showed ~5.6GB, native `ollama pull gemma4:e2b` shows ~7.2GB — likely a
  quantization-default difference between environments, worth a quick check once both
  finish, not urgent)

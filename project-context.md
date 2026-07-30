# Project Context: Privacy-First Local Security Camera Reasoner

## Event
Gemma 4 Hackathon Sprint (GDG on Campus VIT Chennai), 1-day, ~8-10 hour build.
Track: **AI off the Grid** (edge computing — lightweight Gemma models running locally on
mobile/web/IoT/desktop, fast/low-latency/privacy-first, no cloud dependency).

Judging rubric: Gemma Integration (30%), Innovation & Impact (30%), Functionality (20%),
Presentation & Writeup (20%). Submission needs a Kaggle Writeup (<=1500 words), a public
code repo, and a live demo (or clonable notebook).

## The idea
A local security-camera reasoning assistant. Frames come in from a camera feed
(source TBD — likely a phone used as a USB/WiFi webcam via an app like Iriun/DroidCam,
or a pre-recorded/looped video via `cv2.VideoCapture` for demo reliability, possibly
combined with a public live stream as a bonus). Every N seconds (not continuous
streaming — deliberately periodic, framed as a design choice for edge efficiency),
a frame is sent to a locally running Gemma model (E2B or E4B, multimodal, via
Ollama) along with a short rolling history of recent observations.

Gemma's job is NOT simple object/person detection (a bounding-box classifier could do
that). Its job is **contextual reasoning over time**: deciding whether what's happening
is routine or unusual given the situation and history — e.g. "delivery person at door
for 8 seconds, placed a package, left" (normal) vs. "unfamiliar person lingered near
the door for 3 minutes without approaching, returned 3 times in 10 minutes" (flag).
Output should be structured: observation, unusual (bool), severity, and — importantly —
the reasoning behind the judgment (not just a verdict), since transparency/explainability
is a deliberate part of the pitch (see "Known weaknesses" below).

Core technical/architectural decision already made: run entirely inside a Docker
container with hard resource caps (e.g. `--memory=2g --cpus=1`) to simulate real
IoT/edge hardware constraints (Raspberry Pi / Jetson Nano class), with a live on-screen
dashboard showing RAM/CPU/tokens-per-sec during the demo, and a visible network monitor
showing zero outbound traffic (airplane mode / network killed) to prove the offline/
privacy claim concretely rather than asserting it.

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
  design choice, not a limitation).
- **Risk of just being frame-captioning, not real reasoning**: the demo must explicitly
  prove temporal reasoning matters — e.g. showing the same frame produce a different
  verdict depending on injected/fabricated history, side by side.
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

## Stack decided so far
- Ollama running Gemma 4 E2B or E4B (multimodal) locally
- Docker container with hard memory/CPU limits for the edge-hardware simulation
- OpenCV (`cv2.VideoCapture`) for frame capture, source flexible (webcam/phone/video file)
- Some kind of lightweight dashboard for live RAM/CPU/tokens-per-sec + network monitor
  during the demo (exact tooling not yet decided)
- Rolling history of past observations fed back into each Gemma call for temporal context

## Not yet decided / open questions
- Exact camera feed source for the live demo (leaning toward pre-recorded/looped scripted
  scenario clips for reliability, possibly with a live feed as a bonus moment)
- Frame sampling frequency (depends on latency testing)
- Exact prompt/output schema for Gemma's structured response
- Dashboard implementation (Streamlit? simple terminal output? something else?)
- Whether to add any face/identity-familiarity concept ("recognized household member")
  and how, without turning it back into a classifier-first system

This file is context only — no build has started yet in this environment.

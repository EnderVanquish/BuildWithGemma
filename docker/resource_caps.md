# Resource Caps

## Goal
Simulate a basic security camera's onboard processing chip — not an arbitrary round number.

## Research findings
Dedicated security-camera ISPs (e.g. Ambarella CV22/CV25, common in Ring/Nest-class
cameras) are quad-core ~1GHz Arm Cortex-A53 with a dedicated NPU (2-4 TOPS) for on-chip
computer vision — but they run fixed-function CV models on that NPU, not general-purpose
LLM inference via a CPU/RAM budget the way Ollama does, and vendors don't publish RAM specs
for these SoCs. They aren't a fair "can it run Gemma" reference point.

`project-context.md` already framed the target as "Raspberry Pi / Jetson Nano class"
hardware, which is the more honest analogue for "basic edge device with onboard AI
capability, running general inference." Within that class, the **Jetson Nano 2GB Developer
Kit** is the right anchor: it's explicitly marketed as bringing entry-level ML inference to
a Raspberry-Pi-equivalent price point — i.e. the actual budget tier a basic camera-class
edge device would plausibly ship with — while the Nano 4GB / Raspberry Pi 4 (4GB) sit one
tier up.

Reference specs found:
- Jetson Nano: quad-core ARM Cortex-A57 @ 1.43GHz, 2GB or 4GB RAM variants, 128-core Maxwell GPU
- Raspberry Pi 4: quad-core ARM Cortex-A72 @ 1.5GHz, 1/2/4/8GB RAM variants, VideoCore 6 GPU
- Ambarella CV22/CV25: quad-core Cortex-A53 @ 1GHz + dedicated NPU (not a general LLM target)

## Model
Confirmed with the user: `gemma4:e2b` is the correct Ollama tag — an edge-optimized variant
(~5.12B effective footprint) explicitly meant for low-memory devices. This is the model
baked into the image (see `MODEL_NAME` build arg in `docker/Dockerfile`).

## Chosen caps
```
--memory=6g --cpus=2
```
Grounded in the Jetson Nano 4GB board (quad-core @ 1.43GHz, 4GB RAM) as the reference edge
device class, capped to 2 of its 4 cores to keep the constraint meaningful. The memory cap is
set slightly above the Nano's literal 4GB — at 6GB — to give `gemma4:e2b`'s ~5.12B-parameter
footprint (quantized) plus Ollama's own runtime overhead and KV cache enough headroom to
actually load and run without OOM-killing the container; the intent is still to reflect a
genuinely low-memory edge device, not a full workstation, and this number should be revisited
once M1 validation (below) shows real usage. If it turns out `gemma4:e2b` doesn't fit
comfortably even at 6GB, the fallback is trimming the cap only after confirming actual
resident memory via the dashboard's RAM stat (M3), not guessing further.

## Build vs runtime network use (privacy proof integrity)
The Gemma model is pulled into the image **at `docker build` time** (network required), not
at container runtime. This keeps the running container's actual network requirement at zero,
so the demo's "kill the network, dashboard shows zero outbound traffic" proof is genuine
rather than staged around a container that secretly still needs connectivity.

# Argus — a security camera that reasons, running entirely offline

*Track:* AI off the Grid
*Team:* [TEAM NAME]

---

## Problem

Consumer security cameras detect *objects*, not *situations*. They fire "person detected"
at the mail carrier, the neighbour's cat and the person walking off with your parcel with
equal confidence — so owners mute the alerts, and the one notification that mattered is
lost in the noise. The alternative is a cloud subscription that streams continuous video
of your front door to someone else's servers, which is precisely the footage most people
would least like to hand over. Package theft alone affects an estimated 1 in 6 households
annually, and it is a failure of *judgement*, not detection: the camera saw the person
clearly and had no way to tell that leaving with a box is different from arriving with one.

---

## Solution

Argus is a security-camera assistant that watches a scene, and every few seconds asks a
local Gemma 4 model to judge what is happening — given what it has already seen and what it
knows about the location. Instead of a bounding box, each sample produces a short structured
verdict: what is happening, whether it is unusual, a severity, and the reasoning behind it.
Those verdicts accumulate into a log the model then reasons *over*, so it can escalate
("the person from the earlier frames is now walking away with something they arrived
without") rather than re-judging each frame from scratch. A local dashboard shows the live
frame, the current status, the running history, and a free-text box to ask questions about
the log ("was anyone at the door after 10pm?"). A second Config page holds the site-specific
knowledge: what the camera overlooks, where the door and street sit in the frame, and the
household's routines. Everything — model, inference, dashboard — runs inside a single
resource-capped container. No frame is ever written to disk, and nothing leaves the device.

---

## How Gemma Is Used

- *Model variant:* Gemma 4 E2B, instruction-tuned, quantization-aware trained
  (`gemma4:e2b-it-qat`), served by Ollama.
- *How it's used:* Base model, multimodal, no fine-tuning. Each sample sends two images
  (the previous sample and the current frame) plus a text prompt carrying the site context,
  the household routines, the current time, and the rolling observation history. Output is
  constrained to JSON and validated with Pydantic.
- *Why this variant:* Memory was the deciding constraint. The QAT build is 4.34 GB on disk
  versus 7.16 GB for the default post-training-quantized `gemma4:e2b` — about 4.6 GB versus
  5.7 GB resident. Inside a 6 GB cap that is the difference between comfortable headroom and
  running at 97% with swap thrashing. Measured throughput was unchanged (2.11 → 2.21 tok/s
  at the time of the swap), so the memory saving was effectively free. E2B rather than a
  larger variant because the whole claim is that this runs on camera-class hardware.
- *Customization:* Prompt and schema design rather than weights. The system prompt encodes
  the judgement rules the task needs — that an empty history is not evidence of normality,
  that repetition escalates rather than normalizes, that a missing package is itself
  evidence, and that direction of travel separates a courier from a thief. A Pydantic
  validator reconciles contradictory outputs (the model does emit `unusual=false` with a
  non-none severity) by trusting whichever field indicates *more* concern, since
  under-reporting is the worse failure for a security tool.

---

## Architecture

```
      ┌──────────────────── Docker container: --memory=6g --cpus=4 ────────────────────┐
      │                                                                                │
  ┌───┴────┐   frame    ┌───────────────┐   2 images + prompt   ┌──────────────────┐   │
  │ Camera │──────────▶ │ Sampling loop │─────────────────────▶ │ Ollama + Gemma 4 │   │
  │ / clip │  (OpenCV)  │  every N sec  │ ◀───────────────────  │   E2B (QAT)      │   │
  └───┬────┘            └───────┬───────┘    structured JSON    └──────────────────┘   │
      │                         │                                                      │
      │                         ▼                                                      │
      │                 ┌───────────────┐   verdict     ┌──────────────────────┐        │
      │                 │ Routine-window│──────────────▶│ Rolling history      │        │
      │                 │  enforcement  │               │ + in-memory frames   │        │
      │                 └───────────────┘               └──────────┬───────────┘        │
      │                                                            │                    │
      │                                                            ▼                    │
      │                                                 ┌──────────────────────┐        │
      │                                                 │ Flask + SSE          │        │
      │                                                 └──────────┬───────────┘        │
      └────────────────────────────────────────────────────────────┼────────────────────┘
                                                                   ▼
                                                      Dashboard (localhost:5000)
                                                      Monitor page · Config page

  Raw frames exist only for the duration of one inference call. Only text persists.
  No outbound network calls anywhere in the request path.
```

*Tech stack:* Python 3.12, Ollama (llama.cpp), OpenCV, Flask + Server-Sent Events, Pydantic,
psutil, vanilla JS with Tailwind + daisyUI vendored locally (no CDN, so the offline claim
survives a disconnected demo). Deployment target: one Docker image containing Python, Ollama
and the model weights, run under cgroup v2 memory and CPU caps.

---

## Results / Demo

*Reasoning over time, not per-frame captioning.* The system's verdicts change as evidence
accumulates rather than being a function of the current frame alone. The observation log
carries forward, and severity escalates when a later frame contradicts an innocent reading
of an earlier one.

*Real enforcement where the model is unreliable.* Asked to respect routine time windows,
Gemma would cite a routine and acknowledge the time mismatch in the same sentence — *"matches
'Resident leaves for work' (09:40–10:20), although the current time is 14:10 ... it is
considered routine."* Three rounds of increasingly explicit prompting, including a worked
counter-example, did not fix it. Comparing two clock times is not a judgement call, so it was
moved out of the prompt into code: if the reasoning leans on a routine whose window excludes
the current time, the verdict is overridden to `unusual / medium` with a visible explanation.
The model still decides what it *sees*; it just cannot use an inapplicable routine as an
excuse. This is the general pattern used throughout — let Gemma do perception and judgement,
and enforce the arithmetic deterministically.

*Measured under the cap, not on a dev box.* All figures below are from inside the container,
read from cgroup v2 (`memory.current`, `cpu.max`) rather than `psutil`, which reports
host-wide values inside a container and initially made the dashboard claim 15.4 GB against a
6 GB limit:

| Metric | Value |
|---|---|
| Memory cap / observed | 6 GB / ~5.6–5.9 GB |
| CPU quota | 4 cores (enforced, verified via `cpu.max`) |
| Throughput | ~6 tok/s (CPU-only, no GPU) |
| Time per observation | ~90 s |
| Model on disk | 4.34 GB |
| Frames written to disk | 0 |

*Honest limitations.* Direction of travel remains the weak point. A single still cannot show
motion, so the system sends two frames and asks the model to compare positions — this fixed
confidently-wrong single-frame guesses and surfaced the carried object, but the toward/away
judgement is still not reliable enough to trigger the theft rule consistently. Sampling every
N seconds also means brief events can fall between samples. The demo footage is third-party
CCTV used for development only and is not redistributed with the project.

- *Demo video:* [LINK]
- *Screenshots:* [ATTACH: monitor page mid-escalation; config page; history with a selected snapshot]

---

## Links

- *GitHub repo:* https://github.com/EnderVanquish/BuildWithGemma
- *Model:* [google/gemma-4-e2b-it-qat](https://ollama.com/library/gemma4) (Gemma Terms of Use)
- *Dataset(s) used:* None — no training or fine-tuning was performed.
- *License for this project:* [CHOOSE — Apache 2.0 recommended]

---

## Acknowledgments

Built for the Gemma 4 Hackathon Sprint, GDG on Campus VIT Chennai. Thanks to the Ollama and
llama.cpp maintainers — Gemma 4 vision was broken on native Windows during development
(ollama/ollama#16532, #16597, #16874), and tracing that to a platform issue rather than our
own code, then moving development into a Linux container, is what unblocked the project.

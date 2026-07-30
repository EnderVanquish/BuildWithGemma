"""App-wide configuration, env-overridable.

ARGUS_OLLAMA_URL matters more than it looks: Gemma 4 vision is broken on native
Windows Ollama (see project-context.md "Validated findings"), so during development
on Windows this must point at the container's Ollama rather than the host's.
"""

import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Display timezone for observation timestamps. A fixed offset rather than zoneinfo:
# IST has no DST so the offset is exact year-round, and it avoids depending on the
# tzdata package, which Windows doesn't ship.
_tz_offset_minutes = int(os.getenv("DISPLAY_TZ_OFFSET_MINUTES", "330"))  # +05:30 IST
DISPLAY_TZ = timezone(timedelta(minutes=_tz_offset_minutes))

# Low temperature on purpose. Gemma 4's default is 1.0, which for a structured
# judgement task produced visibly unstable verdicts — near-identical frames swung
# none -> medium -> low across consecutive samples. Security judgements need to be
# reproducible, so creativity is not wanted here.
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.15"))

# Free-text description of what this camera watches and what counts as expected.
# This is the "household/context registry": it gives the model the situational
# knowledge a resident has and a frame alone cannot supply (that this is an entrance
# rather than a hallway, when deliveries are normal, that packages get left here).
# Kept as plain text fed into the prompt, deliberately NOT face recognition — that
# would turn the system back into a classifier and undercut the privacy claim.
_site_context_file = Path(__file__).resolve().parents[1] / "site_context.txt"
SITE_CONTEXT = os.getenv("SITE_CONTEXT") or (
    _site_context_file.read_text(encoding="utf-8").strip()
    if _site_context_file.exists() else ""
)

# QAT (quantization-aware trained) rather than the default post-training-quantized
# gemma4:e2b: 4.34GB vs 7.16GB on disk (~3.6GB vs ~5.87GB resident), which is the
# difference between ~2.4GB of headroom in the 6GB cap and running at 97% with swap
# thrashing. QAT holds quality at low precision far better than naive quantization,
# so this is a near-free win rather than a quality-for-size trade.
MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:e2b-it-qat")

# Deliberately NOT called OLLAMA_HOST: Ollama's own server reads that variable to
# decide what address to bind to (the Dockerfile sets it to 0.0.0.0:11434), so reusing
# the name for the client URL would collide and break the server inside the container.
#
# Default assumes dev-on-Windows, where the container publishes Ollama on 11435.
# Inside the container the entrypoint sets ARGUS_OLLAMA_URL=http://localhost:11434.
OLLAMA_URL = os.getenv("ARGUS_OLLAMA_URL", "http://localhost:11435")

# Wall-clock floor between samples. Set ABOVE measured inference time on purpose.
#
# Measured on this hardware: ~132s per observation at 1.6-3.3 tok/s. If this floor is
# set below that (e.g. 10s), the loop never sleeps and the CPU is pegged at 100%
# continuously — which would make the project's "periodic sampling is an
# edge-efficiency choice" claim false, since the device would never idle. Keeping it
# above inference time is what makes that claim actually true.
#
# It also suits the task: "lingered 3 minutes", "returned 3x in 10 minutes" is
# minute-scale reasoning, so sub-10s sampling would add cost without adding signal.
SAMPLE_INTERVAL_SECONDS = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "150"))

# How far to seek forward through a *recorded clip* per sample. Deliberately separate
# from SAMPLE_INTERVAL_SECONDS: that one paces real time, this one controls how much
# of the footage each sample skips. Tune it to the clip length — for a 50s clip, 5s
# gives ~10 distinct moments, whereas reusing a 30s wall-clock interval here would
# yield fewer than 2 before looping.
CLIP_ADVANCE_SECONDS = float(os.getenv("CLIP_ADVANCE_SECONDS", "5"))

HISTORY_MAX_LEN = int(os.getenv("HISTORY_MAX_LEN", "10"))

# Longest-side pixel limit for frames sent to the model. Not arbitrary: full-size
# CCTV frames (e.g. 2732x1440 = 3.9MP) exceed Gemma 4's ~2.6MP input limit and blew
# the vision encoder past the container's memory cap, OOM-killing llama-server.
# Downscaling is also the right thing for an edge device — a person at a door is
# perfectly legible at this size, and it cuts both memory and inference time.
MAX_FRAME_DIM = int(os.getenv("MAX_FRAME_DIM", "768"))

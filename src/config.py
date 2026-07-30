"""App-wide configuration, env-overridable.

OLLAMA_HOST matters more than it looks: Gemma 4 vision is broken on native Windows
Ollama (see project-context.md "Validated findings"), so during development on
Windows this should point at the container's Ollama (default below) rather than the
host's. When the whole stack runs inside the container, the in-container default
(localhost:11434) is correct.
"""

import os

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:e2b")

# Host default assumes the dev-on-Windows case: the container publishes its Ollama
# on 11435. Inside the container, set OLLAMA_HOST=http://localhost:11434.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11435")

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

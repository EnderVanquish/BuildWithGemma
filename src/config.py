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

# Seconds between frame samples. Deliberately periodic rather than continuous —
# an edge-efficiency design choice, and CPU-only inference takes tens of seconds
# per call anyway.
SAMPLE_INTERVAL_SECONDS = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "10"))

HISTORY_MAX_LEN = int(os.getenv("HISTORY_MAX_LEN", "10"))

# Longest-side pixel limit for frames sent to the model. Not arbitrary: full-size
# CCTV frames (e.g. 2732x1440 = 3.9MP) exceed Gemma 4's ~2.6MP input limit and blew
# the vision encoder past the container's memory cap, OOM-killing llama-server.
# Downscaling is also the right thing for an edge device — a person at a door is
# perfectly legible at this size, and it cuts both memory and inference time.
MAX_FRAME_DIM = int(os.getenv("MAX_FRAME_DIM", "768"))

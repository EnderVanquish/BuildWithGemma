import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flask import Flask, Response, jsonify, request, send_from_directory

from capture import LiveStreamSource, VideoFileSource
from config import SAMPLE_INTERVAL_SECONDS
from dashboard.backend.state import DashboardState
from monitor.resources import read_stats
from reasoning.loop import run_reasoning_loop
from reasoning.qa import ask_about_history
from reasoning.schema import ObservationRecord

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

# Frame source for the reasoning loop. FRAME_SOURCE is a video file path (default)
# or, with SOURCE_KIND=stream, an RTSP/HTTP URL for a LAN camera.
FRAME_SOURCE = os.getenv("FRAME_SOURCE", "")
SOURCE_KIND = os.getenv("SOURCE_KIND", "file")

app = Flask(__name__, static_folder=None)
state = DashboardState()


def _stats_loop() -> None:
    while True:
        stats = read_stats(cpu_interval=1.0)
        state.update_stats(
            ram_used_gb=stats.ram_used_gb,
            ram_total_gb=stats.ram_total_gb,
            cpu_pct=stats.cpu_pct,
            stats_source=stats.source,
        )


def _on_observation(record: ObservationRecord, tokens_per_sec: float | None,
                    frame_jpeg: bytes | None) -> None:
    state.add_observation(record)
    if tokens_per_sec is not None:
        state.set_tokens_per_sec(tokens_per_sec)
    if frame_jpeg is not None:
        state.set_frame(frame_jpeg)


def _reasoning_thread() -> None:
    if not FRAME_SOURCE:
        print("[argus] FRAME_SOURCE not set; reasoning loop disabled "
              "(dashboard will show stats only).")
        return

    # A recorded clip advances in video time by the sampling interval, so successive
    # samples show genuinely different moments (as a live camera would) rather than
    # near-identical consecutive frames.
    source = (LiveStreamSource(FRAME_SOURCE) if SOURCE_KIND == "stream"
              else VideoFileSource(FRAME_SOURCE, loop=True,
                                   advance_seconds=SAMPLE_INTERVAL_SECONDS))
    print(f"[argus] reasoning loop starting on {SOURCE_KIND}: {FRAME_SOURCE}")
    run_reasoning_loop(source, _on_observation)


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/stream")
def stream():
    def generate():
        while True:
            yield f"data: {json.dumps(state.snapshot())}\n\n"
            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/frame")
def frame():
    """Serves the most recent reasoned-about frame from memory.

    Served per-request rather than embedded in every SSE tick: the frame only
    changes once per sampling interval, so base64-ing it into a 1Hz stream would
    waste bandwidth for no benefit.
    """
    jpeg = state.get_frame()
    if jpeg is None:
        return "", 204
    return Response(jpeg, mimetype="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.route("/api/ask", methods=["POST"])
def ask():
    question = (request.get_json(silent=True) or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    if not state.history_snapshot():
        return jsonify({"answer": "The log is empty so far — nothing to answer from yet."})

    # Errors are returned as JSON, not Flask's default HTML page: the frontend
    # calls res.json() and an HTML error body surfaces as a useless
    # "Unexpected token '<'" instead of the real cause (e.g. Ollama unreachable).
    try:
        answer = ask_about_history(question, state.history_snapshot())
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 502
    return jsonify({"answer": answer})


if __name__ == "__main__":
    threading.Thread(target=_stats_loop, daemon=True).start()
    threading.Thread(target=_reasoning_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)

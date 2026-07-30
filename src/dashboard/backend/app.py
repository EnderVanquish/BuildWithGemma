import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flask import Flask, Response, jsonify, request, send_from_directory

from dashboard.backend.state import DashboardState
from monitor.resources import read_stats
from reasoning.qa import ask_about_history
from reasoning.schema import ObservationRecord

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

app = Flask(__name__, static_folder=None)
state = DashboardState()

# Seeded so /api/ask has a real log to reason over before the periodic
# vision-based reasoning loop (blocked on the Windows Ollama vision bug, see
# project-context.md) is wired in as the real source of these entries.
for entry in [
    ObservationRecord(timestamp="12:00:00", observation="Empty porch, no activity",
                       unusual=False, severity="none", reasoning="No motion detected."),
    ObservationRecord(timestamp="12:03:00", observation="Delivery person approached, placed a package, left",
                       unusual=False, severity="low", reasoning="Brief presence matches typical delivery behavior."),
    ObservationRecord(timestamp="12:09:00", observation="Unfamiliar person lingered near the door for 3 minutes",
                       unusual=True, severity="medium", reasoning="Duration exceeds typical dwell time."),
]:
    state.add_observation(entry)


def _stats_loop() -> None:
    while True:
        stats = read_stats(cpu_interval=1.0)
        state.update_stats(
            ram_used_gb=stats.ram_used_gb,
            ram_total_gb=stats.ram_total_gb,
            cpu_pct=stats.cpu_pct,
            stats_source=stats.source,
        )


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


@app.route("/api/ask", methods=["POST"])
def ask():
    question = request.get_json(force=True).get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    answer = ask_about_history(question, state.history_snapshot())
    return jsonify({"answer": answer})


if __name__ == "__main__":
    threading.Thread(target=_stats_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)

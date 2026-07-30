"""Periodic frame-sampling reasoning loop.

Deliberately samples every N seconds rather than streaming continuously: an
edge-efficiency design choice, and CPU-only multimodal inference takes tens of
seconds per call under the container's resource cap anyway.

Frames are held in memory only for the duration of one inference call and are never
written to disk — only the resulting text observations persist. That's the concrete
mechanism behind the project's privacy claim.
"""

import time
from collections.abc import Callable

import cv2

from capture.base import FrameSource
from config import HISTORY_MAX_LEN, SAMPLE_INTERVAL_SECONDS

from .client import downscale, reason_about_frame
from .history import RollingHistory
from .schema import ObservationRecord

# (record, tokens_per_sec, frame_jpeg) — frame_jpeg is passed only so the dashboard
# can display the frame that was just reasoned about; it is never persisted.
OnObservation = Callable[[ObservationRecord, float | None, bytes | None], None]


def run_reasoning_loop(
    source: FrameSource,
    on_observation: OnObservation,
    interval_seconds: float = SAMPLE_INTERVAL_SECONDS,
    history: RollingHistory | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> None:
    history = history or RollingHistory(max_len=HISTORY_MAX_LEN)

    while not (stop_check and stop_check()):
        started = time.monotonic()
        frame = source.read_frame()

        if frame is None:
            time.sleep(interval_seconds)
            continue

        # Preview is downscaled the same way the model's input is, so the dashboard
        # shows what the model actually saw (and stays cheap to ship to the browser).
        ok, preview_buf = cv2.imencode(".jpg", downscale(frame))
        frame_jpeg = preview_buf.tobytes() if ok else None

        try:
            record, tokens_per_sec = reason_about_frame(frame, history.entries)
        except Exception as exc:  # keep the loop alive; a bad call shouldn't kill it
            print(f"[reasoning-loop] inference failed: {exc}")
            time.sleep(interval_seconds)
            continue
        finally:
            del frame  # raw frames are never retained beyond the call that used them

        history.add(record)
        on_observation(record, tokens_per_sec, frame_jpeg)

        # Interval is measured from the start of the call, so a slow inference
        # doesn't compound into an ever-growing gap between samples.
        remaining = interval_seconds - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

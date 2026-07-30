"""Same-frame-different-history proof: feeds one fixed frame through the reasoning
pipeline twice, with two different fabricated histories, to demonstrate that the
verdict depends on temporal context rather than the frame alone (see
project-context.md, "Known weaknesses" -> risk of just being frame-captioning)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import cv2

from reasoning.client import reason_about_frame
from reasoning.history import RollingHistory
from reasoning.schema import ObservationRecord

FRAME_PATH = Path(__file__).parent / "shared_frame.jpg"

ROUTINE_HISTORY = [
    ObservationRecord(
        timestamp="12:00:00", observation="Empty porch, no activity",
        unusual=False, severity="none", reasoning="No motion detected.",
    ),
    ObservationRecord(
        timestamp="12:03:00", observation="Delivery van parked on the street",
        unusual=False, severity="none", reasoning="Consistent with expected delivery window.",
    ),
]

ESCALATING_HISTORY = [
    ObservationRecord(
        timestamp="12:00:00", observation="Unfamiliar person walked past the door",
        unusual=False, severity="none", reasoning="Single pass-by, no lingering.",
    ),
    ObservationRecord(
        timestamp="12:05:00", observation="Same person returned, lingered near the door for 2 minutes",
        unusual=True, severity="medium", reasoning="Lingering duration exceeds typical dwell time.",
    ),
    ObservationRecord(
        timestamp="12:09:00", observation="Same person returned a third time, did not approach",
        unusual=True, severity="high", reasoning="Repeated returns without approach break the routine pattern.",
    ),
]


def run() -> None:
    frame = cv2.imread(str(FRAME_PATH))
    if frame is None:
        raise FileNotFoundError(
            f"Place a shared demo frame at {FRAME_PATH} before running this scenario."
        )

    for label, history_entries in [("ROUTINE history", ROUTINE_HISTORY), ("ESCALATING history", ESCALATING_HISTORY)]:
        history = RollingHistory()
        for entry in history_entries:
            history.add(entry)

        result = reason_about_frame(frame, history.entries)
        print(f"\n--- {label} ---")
        print(f"unusual:  {result.unusual}")
        print(f"severity: {result.severity}")
        print(f"observation: {result.observation}")
        print(f"reasoning:   {result.reasoning}")


if __name__ == "__main__":
    run()

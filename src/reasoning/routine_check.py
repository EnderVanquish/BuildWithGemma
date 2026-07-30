"""Deterministic enforcement of routine time windows.

The model repeatedly cites a routine as justification for a "routine" verdict while
acknowledging in the same sentence that the current time is outside that routine's
window — e.g. "matches 'Resident leaves for work' (09:40-10:20), although the current
time is 14:10 ... it is considered routine". Three rounds of increasingly explicit
prompt instructions (including a worked counter-example) did not stop it.

Comparing two clock times is not a judgement call, so it does not belong in the
prompt at all. This module does it in code: if the reasoning leans on a routine whose
window does not contain the current time, the verdict is overridden. The model still
decides what it sees — this only refuses to let an inapplicable routine excuse it.
"""

import re
from datetime import datetime

from config import DISPLAY_TZ, get_routines, get_scene_time

from .schema import ObservationRecord

SEVERITY_ORDER = ["none", "low", "medium", "high"]
# What an out-of-window routine match is escalated to. "medium" rather than "high":
# doing a known activity at the wrong hour is genuinely suspicious, but on its own it
# is not evidence of a crime the way leaving with a package is.
OUT_OF_WINDOW_SEVERITY = "medium"

_TIME = re.compile(r"(\d{1,2}):(\d{2})")


def _minutes(text: str) -> int | None:
    match = _TIME.search(text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return hour * 60 + minute


def _current_minutes() -> int:
    scene = get_scene_time()
    scene_minutes = _minutes(scene) if scene else None
    if scene_minutes is not None:
        return scene_minutes
    now = datetime.now(DISPLAY_TZ)
    return now.hour * 60 + now.minute


def _window(routine: dict) -> tuple[int, int] | None:
    parts = str(routine.get("window", "")).split("-")
    if len(parts) != 2:
        return None
    start, end = _minutes(parts[0]), _minutes(parts[1])
    if start is None or end is None:
        return None
    return start, end


def _contains(window: tuple[int, int], minutes: int) -> bool:
    start, end = window
    # A window like 22:00-02:00 wraps past midnight, so it can't be a simple range test.
    if start <= end:
        return start <= minutes <= end
    return minutes >= start or minutes <= end


def enforce_routine_windows(record: ObservationRecord) -> ObservationRecord:
    """Overrides a "routine" verdict that rests on an out-of-window routine."""
    if record.unusual and record.severity != "none":
        return record  # already flagged; nothing to correct

    now = _current_minutes()
    reasoning = record.reasoning.lower()

    for routine in get_routines():
        label = str(routine.get("label", "")).strip()
        if not label or label.lower() not in reasoning:
            continue
        window = _window(routine)
        if window is None or _contains(window, now):
            continue

        clock = f"{now // 60:02d}:{now % 60:02d}"
        record = record.model_copy(update={
            "unusual": True,
            "severity": OUT_OF_WINDOW_SEVERITY,
            "reasoning": (
                f"{record.reasoning.rstrip()} "
                f"[Argus override: this cites the routine '{label}' "
                f"({routine.get('window')}), but the current time is {clock}, outside "
                f"that window. An out-of-window match is not a routine match, so this "
                f"is flagged rather than excused.]"
            ),
        })
        return record

    return record

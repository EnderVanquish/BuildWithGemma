"""Checks the routine-window override against the exact failure seen in the log.

Run inside the container:  docker exec argus python /app/scripts/test_routine_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reasoning.routine_check import enforce_routine_windows  # noqa: E402
from reasoning.schema import ObservationRecord  # noqa: E402

CASES = [
    (
        "cites out-of-window routine",
        "The activity matches a known routine: 'Resident leaves for work' "
        "(Mon-Fri, 09:40-10:20). Although the current time is Tuesday at 14:10, "
        "which is outside the specified window, it is considered routine.",
        True,
    ),
    (
        "no routine cited",
        "A person is standing on the porch. Nothing about this is concerning.",
        False,
    ),
]

for name, reasoning, should_flag in CASES:
    record = ObservationRecord(
        timestamp="14:10",
        observation="A person walking on the driveway.",
        unusual=False,
        severity="none",
        reasoning=reasoning,
    )
    result = enforce_routine_windows(record)
    ok = result.unusual == should_flag
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: "
          f"unusual={result.unusual} severity={result.severity}")
    if result.unusual:
        print(f"        {result.reasoning[result.reasoning.index('[Argus override'):]}")

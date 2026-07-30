import json
from datetime import datetime, timezone

import cv2
import numpy as np
import ollama

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schema import ObservationRecord

MODEL_NAME = "gemma4:e2b"


def _encode_frame(frame: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Failed to encode frame as JPEG")
    return buf.tobytes()


def reason_about_frame(frame: np.ndarray, history: list[ObservationRecord]) -> ObservationRecord:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(history),
                "images": [_encode_frame(frame)],
            },
        ],
        format="json",
    )
    payload = json.loads(response["message"]["content"])
    return ObservationRecord(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        observation=payload["observation"],
        unusual=payload["unusual"],
        severity=payload["severity"],
        reasoning=payload["reasoning"],
    )

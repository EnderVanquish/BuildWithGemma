import json
from datetime import datetime, timezone

import cv2
import numpy as np
import ollama

from config import MAX_FRAME_DIM, MODEL_NAME, OLLAMA_HOST

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schema import ObservationRecord

_client = ollama.Client(host=OLLAMA_HOST)


def downscale(frame: np.ndarray, max_dim: int = MAX_FRAME_DIM) -> np.ndarray:
    """Shrinks a frame so its longest side is at most max_dim, preserving aspect ratio.

    Required, not cosmetic: full-resolution CCTV frames exceed Gemma 4's input limit
    and OOM-killed the model process inside the capped container.
    """
    height, width = frame.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return frame
    scale = max_dim / longest
    return cv2.resize(
        frame,
        (max(1, int(width * scale)), max(1, int(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _encode_frame(frame: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", downscale(frame))
    if not ok:
        raise ValueError("Failed to encode frame as JPEG")
    return buf.tobytes()


def reason_about_frame(
    frame: np.ndarray, history: list[ObservationRecord]
) -> tuple[ObservationRecord, float | None]:
    """Returns the parsed observation and the measured tokens/sec for this call.

    Ollama reports eval_count/eval_duration per response, so tokens/sec is measured
    from the model's own numbers rather than wall-clock guesswork.
    """
    response = _client.chat(
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
        think=False,
    )

    payload = json.loads(response["message"]["content"])
    record = ObservationRecord(
        timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
        observation=payload["observation"],
        unusual=payload["unusual"],
        severity=payload["severity"],
        reasoning=payload["reasoning"],
    )

    eval_count = response.get("eval_count")
    eval_duration_ns = response.get("eval_duration")
    tokens_per_sec = (
        eval_count / (eval_duration_ns / 1e9)
        if eval_count and eval_duration_ns
        else None
    )
    return record, tokens_per_sec

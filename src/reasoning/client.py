import json
from datetime import datetime

import cv2
import numpy as np
import ollama

from config import DISPLAY_TZ, MAX_FRAME_DIM, MODEL_NAME, OLLAMA_URL, TEMPERATURE

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schema import ObservationRecord

_client = ollama.Client(host=OLLAMA_URL)


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
    frame: np.ndarray,
    history: list[ObservationRecord],
    previous_frame: np.ndarray | None = None,
    avoid_repeating: str | None = None,
) -> tuple[ObservationRecord, float | None]:
    """Returns the parsed observation and the measured tokens/sec for this call.

    When a previous frame is supplied, both images are sent so the model can compare
    them. This is not an optional refinement: direction of travel and "arrived
    empty-handed, leaving with a box" are not recoverable from a single still, and
    asking for them from one frame produced confidently wrong guesses about which way
    a person was walking.

    Ollama reports eval_count/eval_duration per response, so tokens/sec is measured
    from the model's own numbers rather than wall-clock guesswork.
    """
    images = ([_encode_frame(previous_frame)] if previous_frame is not None else []) + [
        _encode_frame(frame)
    ]
    response = _client.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(history,
                                             paired=previous_frame is not None,
                                             avoid_repeating=avoid_repeating),
                "images": images,
            },
        ],
        format="json",
        think=False,
        options={"temperature": TEMPERATURE},
    )

    payload = json.loads(response["message"]["content"])
    record = ObservationRecord(
        timestamp=datetime.now(DISPLAY_TZ).strftime("%H:%M:%S"),
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

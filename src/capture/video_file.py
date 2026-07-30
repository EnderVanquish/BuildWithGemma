import cv2
import numpy as np

from .base import FrameSource


class VideoFileSource(FrameSource):
    """Samples a video file, advancing through it in *video* time.

    `advance_seconds` matters: reading one frame per call would only move 1/30s per
    sample, so consecutive samples would be near-identical and there would be no real
    temporal change for the model to reason about. Advancing by the sampling interval
    instead makes a recorded clip behave like a live camera watched periodically.
    """

    def __init__(self, path: str, loop: bool = True, advance_seconds: float = 0.0):
        self._loop = loop
        self._advance_seconds = advance_seconds
        self._cap = cv2.VideoCapture(path)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    def read_frame(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        if not ok and self._loop:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        if not ok:
            return None

        if self._advance_seconds > 0:
            step = int(self._advance_seconds * self._fps)
            target = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) + step
            if self._frame_count and target >= self._frame_count:
                target = 0 if self._loop else self._frame_count - 1
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, target)

        return frame

    def release(self) -> None:
        self._cap.release()

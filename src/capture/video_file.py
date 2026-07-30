import cv2
import numpy as np

from .base import FrameSource


class VideoFileSource(FrameSource):
    def __init__(self, path: str, loop: bool = True):
        self._loop = loop
        self._cap = cv2.VideoCapture(path)

    def read_frame(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        if not ok and self._loop:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        self._cap.release()

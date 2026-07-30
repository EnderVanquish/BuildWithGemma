import cv2
import numpy as np

from .base import FrameSource


class LiveStreamSource(FrameSource):
    """RTSP/HTTP camera stream, e.g. a phone running the 'IP Webcam' app on the
    same LAN (no cloud relay — see project-context.md privacy proof)."""

    def __init__(self, url: str):
        self._cap = cv2.VideoCapture(url)

    def read_frame(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        self._cap.release()

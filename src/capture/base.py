from abc import ABC, abstractmethod

import numpy as np


class FrameSource(ABC):
    @abstractmethod
    def read_frame(self) -> np.ndarray | None:
        ...

    @abstractmethod
    def release(self) -> None:
        ...

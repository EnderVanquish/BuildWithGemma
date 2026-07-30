from collections import deque

from .schema import ObservationRecord

DEFAULT_MAX_LEN = 10


class RollingHistory:
    def __init__(self, max_len: int = DEFAULT_MAX_LEN):
        self._entries: deque[ObservationRecord] = deque(maxlen=max_len)

    def add(self, record: ObservationRecord) -> None:
        self._entries.append(record)

    @property
    def entries(self) -> list[ObservationRecord]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()

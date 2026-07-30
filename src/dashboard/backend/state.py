import threading
import time

from reasoning.schema import ObservationRecord


class DashboardState:
    def __init__(self, ram_total_gb: float = 6.0):
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.ram_used_gb = 0.0
        self.ram_total_gb = ram_total_gb
        self.cpu_pct = 0.0
        self.tokens_per_sec: float | None = None
        self.network_status = "good"
        self.stats_source = "host"
        self.history: list[ObservationRecord] = []
        # Latest frame, JPEG-encoded, held in memory only so the dashboard can show
        # what was just reasoned about. Never written to disk — that's the privacy claim.
        self.latest_frame_jpeg: bytes | None = None
        self.frame_id = 0

    def set_tokens_per_sec(self, tokens_per_sec: float) -> None:
        with self._lock:
            self.tokens_per_sec = tokens_per_sec

    def set_frame(self, frame_jpeg: bytes) -> None:
        with self._lock:
            self.latest_frame_jpeg = frame_jpeg
            self.frame_id += 1

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self.latest_frame_jpeg

    def update_stats(self, ram_used_gb: float, ram_total_gb: float,
                     cpu_pct: float, stats_source: str) -> None:
        with self._lock:
            self.ram_used_gb = ram_used_gb
            self.ram_total_gb = ram_total_gb
            self.cpu_pct = cpu_pct
            self.stats_source = stats_source

    def add_observation(self, observation: ObservationRecord) -> None:
        with self._lock:
            self.history.append(observation)

    def snapshot(self) -> dict:
        with self._lock:
            latest = self.history[-1] if self.history else None
            return {
                "uptime_seconds": int(time.time() - self.start_time),
                "ram_used_gb": round(self.ram_used_gb, 1),
                "ram_total_gb": round(self.ram_total_gb, 1),
                "cpu_pct": round(self.cpu_pct, 0),
                "tokens_per_sec": self.tokens_per_sec,
                "network_status": self.network_status,
                "stats_source": self.stats_source,
                "frame_id": self.frame_id,
                "latest_observation": latest.model_dump() if latest else None,
                "history": [o.model_dump() for o in self.history[-8:]],
            }

    def history_snapshot(self) -> list[ObservationRecord]:
        with self._lock:
            return list(self.history)

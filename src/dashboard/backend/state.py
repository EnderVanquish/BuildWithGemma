import threading
import time

from reasoning.schema import ObservationRecord

# How many past snapshots stay replayable. Comfortably more than the history the
# dashboard renders, so every visible row has a frame behind it.
RETAINED_FRAMES = 32


class DashboardState:
    def __init__(self, ram_total_gb: float = 6.0):
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.ram_used_gb = 0.0
        self.ram_total_gb = ram_total_gb
        self.cpu_pct = 0.0
        self.cpu_cores = 0.0
        self.tokens_per_sec: float | None = None
        self.network_status = "good"
        self.stats_source = "host"
        self.history: list[ObservationRecord] = []
        # Frames the model actually reasoned about, JPEG-encoded, kept in memory only
        # so the dashboard can replay any past observation's snapshot. Never written to
        # disk — that's the privacy claim, and it survives this feature.
        self.latest_frame_jpeg: bytes | None = None
        self.frame_id = 0
        self._frames: dict[int, bytes] = {}
        # frame_id belonging to each history entry, appended in lockstep with history
        # so a row and its snapshot can never drift apart.
        self.frame_refs: list[int] = []

    def record_observation(self, observation: ObservationRecord,
                          tokens_per_sec: float | None,
                          frame_jpeg: bytes | None) -> None:
        """Commits an observation and its frame together, under one lock.

        These must not be separate calls: a snapshot landing between them would pair
        the new observation with the *previous* frame, so the dashboard would show
        reasoning that describes something other than the image beside it — which for
        a security tool reads as the model hallucinating.
        """
        with self._lock:
            self.history.append(observation)
            if tokens_per_sec is not None:
                self.tokens_per_sec = tokens_per_sec
            if frame_jpeg is not None:
                self.latest_frame_jpeg = frame_jpeg
                self.frame_id += 1
                self._frames[self.frame_id] = frame_jpeg
                self._evict_old_frames()
            self.frame_refs.append(self.frame_id)

    def _evict_old_frames(self) -> None:
        """Bounds retained snapshots. Caller must already hold the lock.

        Unbounded retention would grow without limit inside a 6 GB cap, and only the
        rows the dashboard still shows are reachable anyway.
        """
        while len(self._frames) > RETAINED_FRAMES:
            del self._frames[min(self._frames)]

    def get_frame(self, frame_id: int | None = None) -> bytes | None:
        """Returns a specific retained snapshot, or the latest when frame_id is None."""
        with self._lock:
            if frame_id is None:
                return self.latest_frame_jpeg
            return self._frames.get(frame_id)

    def update_stats(self, ram_used_gb: float, ram_total_gb: float,
                     cpu_pct: float, stats_source: str,
                     cpu_cores: float = 0.0) -> None:
        with self._lock:
            self.ram_used_gb = ram_used_gb
            self.ram_total_gb = ram_total_gb
            self.cpu_pct = cpu_pct
            self.cpu_cores = cpu_cores
            self.stats_source = stats_source

    def snapshot(self) -> dict:
        with self._lock:
            latest = self.history[-1] if self.history else None
            return {
                "uptime_seconds": int(time.time() - self.start_time),
                "ram_used_gb": round(self.ram_used_gb, 1),
                "ram_total_gb": round(self.ram_total_gb, 1),
                "cpu_pct": round(self.cpu_pct, 0),
                "cpu_cores": self.cpu_cores,
                "tokens_per_sec": self.tokens_per_sec,
                "network_status": self.network_status,
                "stats_source": self.stats_source,
                "frame_id": self.frame_id,
                "latest_observation": latest.model_dump() if latest else None,
                "history": [
                    {**o.model_dump(), "frame_ref": ref}
                    for o, ref in zip(self.history[-8:], self.frame_refs[-8:])
                ],
            }

    def history_snapshot(self) -> list[ObservationRecord]:
        with self._lock:
            return list(self.history)

"""Resource stats for the dashboard.

Reads the container's *cgroup* memory usage when running under Docker rather than
`psutil.virtual_memory()`, which reports host-wide memory even inside a container
(it reads /proc/meminfo, which isn't namespaced). Getting this right matters: the
dashboard's whole claim is "this is real usage under a real cap", so reporting the
host's memory would misrepresent it.
"""

from dataclasses import dataclass
from pathlib import Path

import psutil

CGROUP_V2_USAGE = Path("/sys/fs/cgroup/memory.current")
CGROUP_V2_LIMIT = Path("/sys/fs/cgroup/memory.max")
CGROUP_V1_USAGE = Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")
CGROUP_V1_LIMIT = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")

BYTES_PER_GB = 1024 ** 3
# cgroup v1 reports "no limit" as a huge sentinel value rather than a keyword.
NO_LIMIT_SENTINEL = 2 ** 62


@dataclass
class ResourceStats:
    ram_used_gb: float
    ram_total_gb: float
    cpu_pct: float
    source: str  # "cgroup" (real container cap) or "host" (dev fallback)


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _cgroup_memory() -> tuple[float, float] | None:
    """Returns (used_gb, limit_gb) from cgroup v2 or v1, or None if unavailable."""
    for usage_path, limit_path in ((CGROUP_V2_USAGE, CGROUP_V2_LIMIT),
                                   (CGROUP_V1_USAGE, CGROUP_V1_LIMIT)):
        used = _read_int(usage_path)
        if used is None:
            continue

        raw_limit = limit_path.read_text().strip() if limit_path.exists() else ""
        if raw_limit == "max":
            return None  # cgroup exists but uncapped: not a meaningful cap to show
        limit = _read_int(limit_path)
        if limit is None or limit >= NO_LIMIT_SENTINEL:
            return None

        return used / BYTES_PER_GB, limit / BYTES_PER_GB
    return None


def read_stats(cpu_interval: float = 1.0) -> ResourceStats:
    cpu_pct = psutil.cpu_percent(interval=cpu_interval)

    cgroup = _cgroup_memory()
    if cgroup is not None:
        used_gb, limit_gb = cgroup
        return ResourceStats(used_gb, limit_gb, cpu_pct, source="cgroup")

    memory = psutil.virtual_memory()
    return ResourceStats(
        ram_used_gb=memory.used / BYTES_PER_GB,
        ram_total_gb=memory.total / BYTES_PER_GB,
        cpu_pct=cpu_pct,
        source="host",
    )

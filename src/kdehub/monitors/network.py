import time

import psutil

from kdehub.core import Reading, format_rate

NAME = "Network"
INTERVAL = 2

_last = None


def read(cfg):
    """Current throughput across all interfaces (not an internet speed test)."""
    global _last
    counters = psutil.net_io_counters()
    now = time.monotonic()
    prev, _last = _last, (now, counters.bytes_recv, counters.bytes_sent)
    if prev is None:
        return [Reading("Download", "…"), Reading("Upload", "…")]
    dt = now - prev[0]
    return [
        Reading("Download", format_rate((counters.bytes_recv - prev[1]) / dt)),
        Reading("Upload", format_rate((counters.bytes_sent - prev[2]) / dt)),
    ]

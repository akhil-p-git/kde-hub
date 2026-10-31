import psutil

from kdehub.core import Reading, level_for

NAME = "Memory"
INTERVAL = 3


def read(cfg):
    mem = psutil.virtual_memory()
    gib = 1024**3
    return [
        Reading("RAM", f"{mem.used / gib:.1f} / {mem.total / gib:.1f} GiB ({mem.percent:.0f}%)",
                level_for(mem.percent, 80, 92)),
    ]

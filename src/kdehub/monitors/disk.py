import os

import psutil

from kdehub.core import Reading, level_for

NAME = "Disk"
INTERVAL = 60
DEFAULT_PATHS = ["/", "/home", "~/work"]


def read(cfg):
    gib = 1024**3
    out = []
    for path in cfg.get("paths", DEFAULT_PATHS):
        usage = psutil.disk_usage(os.path.expanduser(path))
        out.append(Reading(
            path, f"{usage.used / gib:.0f} / {usage.total / gib:.0f} GiB ({usage.percent:.0f}%)",
            level_for(usage.percent, cfg.get("warn", 80), cfg.get("crit", 92))))
    return out

import psutil

from kdehub.core import Reading, level_for

NAME = "CPU"
INTERVAL = 2


def read(cfg):
    pct = psutil.cpu_percent(interval=None)
    freq = psutil.cpu_freq()
    out = [Reading("Usage", f"{pct:.0f}%", level_for(pct, 80, 95))]
    if freq:
        out.append(Reading("Clock", f"{freq.current / 1000:.2f} GHz"))
    return out

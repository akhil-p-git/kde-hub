import psutil

from kdehub.core import Reading, level_for

NAME = "Temperatures"
INTERVAL = 5

# sensor chip -> (row label, preferred sensor label, warn, crit)
CHIPS = {
    "coretemp": ("CPU package", "Package id 0", 80, 95),
    "k10temp": ("CPU", "Tctl", 80, 95),
    "nvme": ("NVMe", "Composite", 70, 80),
}


def pick(entries, preferred):
    for e in entries:
        if e.label == preferred:
            return e
    return entries[0]


def read(cfg):
    sensors = psutil.sensors_temperatures()
    out = []
    for chip, (label, preferred, warn, crit) in CHIPS.items():
        if chip in sensors and sensors[chip]:
            cur = pick(sensors[chip], preferred).current
            out.append(Reading(label, f"{cur:.0f}°C", level_for(cur, warn, crit)))
    if not out:
        raise RuntimeError("no known temperature sensors found")
    return out

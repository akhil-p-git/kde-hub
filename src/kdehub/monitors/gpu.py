import subprocess

from kdehub.core import Reading, level_for

NAME = "GPU"
INTERVAL = 3
QUERY = "name,utilization.gpu,memory.used,memory.total,temperature.gpu"


def parse(line):
    name, util, used, total, temp = (p.strip() for p in line.split(","))
    return [
        Reading("Model", name),
        Reading("Load", f"{util}%", level_for(float(util), 85, 98)),
        Reading("VRAM", f"{float(used) / 1024:.1f} / {float(total) / 1024:.1f} GiB",
                level_for(float(used) / float(total) * 100, 85, 95)),
        Reading("Temp", f"{temp}°C", level_for(float(temp), 80, 90)),
    ]


def read(cfg):
    out = subprocess.run(
        ["nvidia-smi", f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5, check=True,
    ).stdout
    return parse(out.strip().splitlines()[0])

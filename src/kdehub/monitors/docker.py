import json
import subprocess

from kdehub.core import OK, WARN, Reading

NAME = "Docker"
INTERVAL = 30

DF_ROWS = {"Images": "Images", "Local Volumes": "Volumes", "Build Cache": "Build cache"}


def _docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=15, check=True).stdout


def parse(ps_lines, df_lines):
    running = sum(1 for line in ps_lines if line.split("|", 1)[0] == "running")
    unhealthy = sum(1 for line in ps_lines if "(unhealthy)" in line)
    out = [Reading("Containers", f"{running} running / {len(ps_lines)} total")]
    if unhealthy:
        out.append(Reading("Unhealthy", str(unhealthy), WARN))
    for row in map(json.loads, df_lines):
        if row["Type"] in DF_ROWS:
            out.append(Reading(DF_ROWS[row["Type"]], f"{row['Size']} ({row['Reclaimable'].split()[0]} reclaimable)", OK))
    return out


def read(cfg):
    ps = _docker("ps", "-a", "--format", "{{.State}}|{{.Status}}").splitlines()
    df = _docker("system", "df", "--format", "{{json .}}").splitlines()
    return parse(ps, df)

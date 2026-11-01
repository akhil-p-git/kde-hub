import json
import subprocess

from kdehub.core import OK, WARN, Reading

NAME = "npm (global)"
INTERVAL = 3600
SHOWN = 6


def parse(payload):
    if not payload:
        return [Reading("Updates", "up to date")]
    names = [f"{name} {info['current']} → {info['latest']}" for name, info in sorted(payload.items())]
    return [Reading("Updates", f"{len(names)} available", WARN)] + [
        Reading("Package", n, OK) for n in names[:SHOWN]] + (
        [Reading("More", f"+{len(names) - SHOWN} more", OK)] if len(names) > SHOWN else [])


def read(cfg):
    # npm outdated exits 1 when something is outdated, but also for real failures such as no
    # network; those print nothing to stdout and an error to stderr
    proc = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, timeout=120)
    failed = proc.returncode not in (0, 1) or (proc.returncode == 1 and not proc.stdout.strip() and proc.stderr.strip())
    if failed:
        raise RuntimeError(proc.stderr.strip() or f"npm exited {proc.returncode}")
    return parse(json.loads(proc.stdout or "{}"))

import subprocess

from kdehub.core import OK, WARN, Reading

NAME = "AUR"
INTERVAL = 1800


def parse(stdout):
    pkgs = [line.split()[0] for line in stdout.splitlines() if line.strip()]
    if not pkgs:
        return [Reading("Updates", "up to date")]
    names = ", ".join(pkgs)
    return [Reading("Updates", f"{len(pkgs)} available", WARN), Reading("Packages", names, OK)]


def read(cfg):
    # yay -Qua exits 1 with no output when nothing is outdated
    proc = subprocess.run(["yay", "-Qua"], capture_output=True, text=True, timeout=120)
    if proc.stdout.strip() or proc.returncode == 0 or (proc.returncode == 1 and not proc.stderr.strip()):
        return parse(proc.stdout)
    raise RuntimeError(proc.stderr.strip() or f"yay exited {proc.returncode}")

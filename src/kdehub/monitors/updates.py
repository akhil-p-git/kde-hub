import subprocess

from kdehub.core import OK, WARN, Reading

NAME = "Pacman"
INTERVAL = 1800


def parse(stdout):
    pkgs = [line.split()[0] for line in stdout.splitlines() if line.strip()]
    if not pkgs:
        return [Reading("Updates", "up to date")]
    out = [Reading("Updates", f"{len(pkgs)} available", WARN)]
    out.append(Reading("Packages", ", ".join(pkgs), OK))
    return out


def read(cfg):
    # checkupdates (pacman-contrib) exits 2 when there are no updates
    proc = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=120)
    if proc.returncode == 2:
        return parse("")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"checkupdates exited {proc.returncode}")
    return parse(proc.stdout)

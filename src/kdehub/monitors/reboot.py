import os
import platform

from kdehub.core import CRIT, Reading

NAME = "Reboot"
INTERVAL = 300
MODULES_DIR = "/usr/lib/modules"


def needs_reboot(running, modules_dir=MODULES_DIR):
    """The running kernel's module dir disappears once pacman upgrades `linux`."""
    return running not in os.listdir(modules_dir)


def read(cfg):
    running = platform.release()
    if needs_reboot(running):
        return [Reading("Reboot", "needed (kernel upgraded)", CRIT), Reading("Running", running)]
    return [Reading("Reboot", "not needed"), Reading("Kernel", running)]

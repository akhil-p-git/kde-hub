# kde-hub

A system tray app for KDE Plasma that shows machine and weather readings in one popup. Written in Python with PySide6 (Qt 6). The tray icon shows the current CPU % and turns amber or red when any reading crosses a threshold; a red reading also sends a desktop notification. Click the icon to open the popup.

Monitors:

| Section | Shows | Source |
| --- | --- | --- |
| CPU, Memory | usage, clock, RAM used | `psutil` |
| GPU | model, load, VRAM, temperature | `nvidia-smi` (NVIDIA only) |
| Temperatures | CPU package, NVMe | `psutil` sensors (`coretemp`, `k10temp`, `nvme`) |
| Network | current download and upload throughput | `psutil` |
| Disk | used / total per path | `psutil` |
| Docker | container counts, image/volume/build-cache size | `docker ps`, `docker system df` |
| Weather | temperature, sky, high/low, rain chance, UV, sunrise/sunset | [Open-Meteo](https://open-meteo.com/) |
| Pacman | pending updates | `checkupdates` (`pacman-contrib`) |
| Reboot | whether the running kernel was upgraded away | `/usr/lib/modules` |

Network is throughput, not an internet speed test. Pacman and Reboot are Arch-specific; the rest should work on any Linux with the listed tools. I have only run it on Arch Linux with Plasma 6 on Wayland.

## Run

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/akhil-p-git/kde-hub
cd kde-hub
make run        # uv run kde-hub --show: starts the tray app and opens the popup
make test       # uv run pytest
make install    # start on login, and copy config.toml to ~/.config/kde-hub/
```

On Wayland the popup opens as an ordinary window; apps cannot place windows next to the tray icon there.

## Configure

The app reads `~/.config/kde-hub/config.toml` if it exists, otherwise the `config.toml` in the repo. Restart the app after editing.

- Sections appear in the popup in the order they are listed. Monitors not listed still run, after the listed ones.
- `enabled = false` in a section turns that monitor off.
- `[home]` holds the name and coordinates used by weather. Set these to your location.
- Other keys are passed to the monitor: `paths`, `warn`, `crit` for `[disk]`; `unit` for `[weather]`.

## Add a monitor

Create `src/kdehub/monitors/<name>.py`. It is discovered automatically; add a `[<name>]` section to `config.toml` to choose where it appears.

```python
from kdehub.core import Reading, level_for

NAME = "Load"        # section title in the popup
INTERVAL = 5         # seconds between reads


def read(cfg):       # cfg: the monitor's section layered over [home]
    one_min = open("/proc/loadavg").read().split()[0]
    return [Reading("1 min", one_min, level_for(float(one_min), 4, 8))]
```

`level_for(value, warn, crit)` returns `"ok"`, `"warn"` or `"crit"`. Reads run on worker threads. An exception in `read` shows up as an error row instead of stopping the app.

## Limits

- Thresholds are hardcoded in each monitor except Disk.
- No history or graphs; each row is the latest reading.
- Config changes need a restart.

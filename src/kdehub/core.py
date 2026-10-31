"""Monitor contract and discovery.

A monitor is a module in kdehub.monitors that defines:
    NAME: str            title shown in the popup
    INTERVAL: float      seconds between reads
    read(cfg: dict) -> list[Reading]
"""
from __future__ import annotations

import importlib
import json
import pkgutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from types import ModuleType

OK, WARN, CRIT = "ok", "warn", "crit"


@dataclass(frozen=True)
class Reading:
    label: str
    value: str
    level: str = OK


def level_for(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return CRIT
    if value >= warn:
        return WARN
    return OK


def format_rate(bytes_per_s: float) -> str:
    rate = float(bytes_per_s)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if rate < 1024 or unit == "GB/s":
            return f"{rate:.0f} {unit}" if unit == "B/s" else f"{rate:.1f} {unit}"
        rate /= 1024
    raise AssertionError("unreachable")


def monitor_cfg(config: dict, key: str) -> dict:
    """A monitor's own section layered over the shared [home] section."""
    return {**config.get("home", {}), **config.get(key, {})}


def get_json(url: str, params: dict | None = None, headers: dict | None = None, timeout: float = 10):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def discover(config: dict[str, dict]) -> list[ModuleType]:
    """Import every monitor module that is not disabled in config."""
    from kdehub import monitors

    found = []
    order = {name: i for i, name in enumerate(config)}  # popup order follows config.toml
    available = sorted(pkgutil.iter_modules(monitors.__path__), key=lambda i: (order.get(i.name, len(order)), i.name))
    for info in available:
        if config.get(info.name, {}).get("enabled", True) is False:
            continue
        found.append(importlib.import_module(f"kdehub.monitors.{info.name}"))
    return found


def safe_read(module: ModuleType, cfg: dict) -> list[Reading]:
    try:
        return list(module.read(cfg))
    except Exception as exc:  # a failing monitor must show up as a row, not kill the app
        return [Reading("error", f"{type(exc).__name__}: {exc}", WARN)]

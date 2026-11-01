import subprocess
from types import SimpleNamespace

import pytest

from kdehub import core
from kdehub.core import CRIT, OK, WARN, format_rate, level_for
from kdehub.monitors import aur, disk, docker, gpu, network, npm, reboot, updates, weather


def test_level_for_thresholds():
    assert [level_for(v, 80, 95) for v in (10, 80, 94, 95)] == [OK, WARN, WARN, CRIT]


def test_format_rate():
    assert format_rate(512) == "512 B/s"
    assert format_rate(1536) == "1.5 KB/s"
    assert format_rate(5 * 1024**2) == "5.0 MB/s"


def test_discover_finds_all_and_honours_disabled():
    names = {m.__name__.rsplit(".", 1)[-1] for m in core.discover({})}
    assert {"cpu", "ram", "gpu", "temps", "network", "updates", "reboot", "weather", "disk", "docker", "aur", "npm"} <= names
    assert "cpu" not in {m.__name__.rsplit(".", 1)[-1] for m in core.discover({"cpu": {"enabled": False}})}


def test_safe_read_turns_exception_into_row():
    boom = SimpleNamespace(read=lambda cfg: 1 / 0)
    (row,) = core.safe_read(boom, {})
    assert row.level == WARN and "ZeroDivisionError" in row.value


def test_gpu_parse():
    rows = {r.label: r for r in gpu.parse("NVIDIA GeForce RTX 4060, 28, 1782, 8188, 52")}
    assert rows["Load"].value == "28%"
    assert rows["VRAM"].value == "1.7 / 8.0 GiB"
    assert rows["Temp"].value == "52°C" and rows["Temp"].level == OK
    assert gpu.parse("x, 99, 100, 8000, 91")[3].level == CRIT


def test_network_rate_from_counter_delta(monkeypatch):
    ticks = iter([100.0, 102.0])
    counters = iter([SimpleNamespace(bytes_recv=0, bytes_sent=0),
                     SimpleNamespace(bytes_recv=2048, bytes_sent=4096)])
    monkeypatch.setattr(network, "_last", None)
    monkeypatch.setattr(network.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(network.psutil, "net_io_counters", lambda: next(counters))
    network.read({})
    down, up = network.read({})
    assert (down.value, up.value) == ("1.0 KB/s", "2.0 KB/s")


def test_reboot_detects_missing_module_dir(tmp_path):
    (tmp_path / "7.2.12-arch1-1").mkdir()
    assert reboot.needs_reboot("7.2.11-arch1-1", str(tmp_path))
    assert not reboot.needs_reboot("7.2.12-arch1-1", str(tmp_path))


@pytest.mark.parametrize("code,out,expected", [
    (2, "", "up to date"),
    (0, "linux 7.2.11-1 -> 7.2.12-1\nfirefox 1 -> 2\n", "2 available"),
])
def test_updates_read(monkeypatch, code, out, expected):
    monkeypatch.setattr(updates.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, code, out, ""))
    assert updates.read({})[0].value == expected


def test_updates_error_raises(monkeypatch):
    monkeypatch.setattr(updates.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "db locked"))
    with pytest.raises(RuntimeError, match="db locked"):
        updates.read({})


WEATHER = {
    "current": {"temperature_2m": 60.8, "weather_code": 2},
    "daily": {"temperature_2m_max": [67.2], "temperature_2m_min": [50.0],
              "precipitation_probability_max": [1], "uv_index_max": [8.4],
              "sunrise": ["2026-10-30T07:31"], "sunset": ["2026-10-30T18:11"]},
}


def test_weather_parse():
    rows = {r.label: r for r in weather.parse(WEATHER, "San Ramon, CA")}
    assert rows["San Ramon, CA"].value == "61°F"
    assert rows["Sky"].value == "Partly cloudy"
    assert rows["High / low"].value == "67° / 50°"
    assert rows["Rain chance"].value == "1%"
    assert rows["Sun"].value == "7:31 AM – 6:11 PM"
    assert rows["UV (max today)"].level == CRIT


def test_monitor_cfg_layers_home_under_section():
    config = {"home": {"latitude": 1, "name": "A"}, "weather": {"name": "B", "unit": "celsius"}}
    assert core.monitor_cfg(config, "weather") == {"latitude": 1, "name": "B", "unit": "celsius"}
    assert core.monitor_cfg(config, "cpu") == {"latitude": 1, "name": "A"}


def test_discover_follows_config_order():
    names = [m.__name__.rsplit(".", 1)[-1] for m in core.discover({"weather": {}, "cpu": {}})]
    assert names[:2] == ["weather", "cpu"]


def test_disk_levels_follow_thresholds(monkeypatch):
    usage = SimpleNamespace(used=45 * 1024**3, total=50 * 1024**3, percent=90.0)
    monkeypatch.setattr(disk.psutil, "disk_usage", lambda path: usage)
    assert disk.read({"paths": ["/"]})[0].level == WARN
    assert disk.read({"paths": ["/"], "crit": 85})[0].level == CRIT
    assert disk.read({"paths": ["/"]})[0].value == "45 / 50 GiB (90%)"


def test_disk_expands_home(monkeypatch):
    seen = []
    monkeypatch.setattr(disk.psutil, "disk_usage",
                        lambda path: seen.append(path) or SimpleNamespace(used=0, total=1, percent=0))
    disk.read({"paths": ["~/work"]})
    assert seen[0].startswith("/") and "~" not in seen[0]


DF = [
    '{"Reclaimable":"28.7MB (0%)","Size":"5.361GB","Type":"Images"}',
    '{"Reclaimable":"4.17MB (100%)","Size":"4.17MB","Type":"Containers"}',
    '{"Reclaimable":"845.3MB (81%)","Size":"1.041GB","Type":"Local Volumes"}',
]


def test_docker_parse_counts_and_unhealthy():
    ps = ["running|Up 2 hours (healthy)", "running|Up 1 hour (unhealthy)", "exited|Exited (0) 3 days ago"]
    rows = {r.label: r for r in docker.parse(ps, DF)}
    assert rows["Containers"].value == "2 running / 3 total"
    assert rows["Unhealthy"].level == WARN
    assert rows["Volumes"].value == "1.041GB (845.3MB reclaimable)"
    assert "Containers" in rows and len(rows) == 4


def test_docker_parse_no_unhealthy_row_when_healthy():
    assert "Unhealthy" not in {r.label for r in docker.parse(["running|Up 1 hour"], DF)}


def test_render_section_escapes_markup():
    from kdehub.app import render_section
    out = render_section([core.Reading("<b>x</b>", '<img src="file:///etc/passwd"> & more', WARN)])
    assert "<img" not in out and "<b>" not in out
    assert "&lt;img" in out and "&amp; more" in out


@pytest.mark.parametrize("code,out,err,expected", [
    (1, "", "", "up to date"),
    (0, "", "", "up to date"),
    (0, "foo-bin 1.0-1 -> 1.1-1\nbar 2 -> 3\n", "", "2 available"),
    (1, "foo-bin 1.0-1 -> 1.1-1\n", "", "1 available"),
])
def test_aur_read(monkeypatch, code, out, err, expected):
    monkeypatch.setattr(aur.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, code, out, err))
    assert aur.read({})[0].value == expected


def test_aur_error_raises(monkeypatch):
    monkeypatch.setattr(aur.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "error: failed to connect"))
    with pytest.raises(RuntimeError, match="failed to connect"):
        aur.read({})


# shape taken from a real `npm outdated -g --json` run
NPM_OUTDATED = ('{"is-odd": {"current": "1.0.0", "wanted": "3.0.1", "latest": "3.0.1", '
                '"dependent": "global", "location": "/x/is-odd"}}')


def test_npm_read_outdated_exit_1_is_not_an_error(monkeypatch):
    monkeypatch.setattr(npm.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, NPM_OUTDATED, ""))
    rows = npm.read({})
    assert rows[0].value == "1 available" and rows[0].level == WARN
    assert rows[1].value == "is-odd 1.0.0 → 3.0.1"


def test_npm_read_up_to_date(monkeypatch):
    monkeypatch.setattr(npm.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "{}\n", ""))
    assert npm.read({})[0].value == "up to date"


def test_npm_read_exit_1_with_no_output_and_an_error_raises(monkeypatch):
    # npm also exits 1 for real failures such as no network; that must not read as "up to date"
    monkeypatch.setattr(npm.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "npm error code EAI_AGAIN"))
    with pytest.raises(RuntimeError, match="EAI_AGAIN"):
        npm.read({})


def test_npm_read_failure_raises(monkeypatch):
    monkeypatch.setattr(npm.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 2, "", "boom"))
    with pytest.raises(RuntimeError, match="boom"):
        npm.read({})


def test_npm_caps_listed_packages():
    payload = {f"p{i}": {"current": "1", "latest": "2"} for i in range(9)}
    rows = npm.parse(payload)
    assert rows[0].value == "9 available" and rows[-1].value == "+3 more" and len(rows) == 8


def test_pending_updates_sums_update_monitors_only():
    R = core.Reading
    last = {"updates": [R("Updates", "3 available", WARN)], "aur": [R("Updates", "up to date")],
            "npm": [R("Updates", "2 available", WARN), R("Package", "x 1 → 2")],
            "cpu": [R("Usage", "55%")]}
    assert core.pending_updates(last) == 5
    assert core.pending_updates({"cpu": [R("Usage", "55%")]}) is None
    assert core.pending_updates({"npm": [R("error", "RuntimeError: boom", WARN)]}) is None

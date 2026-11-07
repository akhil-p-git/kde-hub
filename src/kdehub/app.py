"""System tray app: runs monitors on their intervals, shows them in a popup window."""
from __future__ import annotations

import html
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QLabel, QMenu, QScrollArea,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from kdehub.core import CRIT, WARN, Reading, discover, monitor_cfg, pending_updates, safe_read

CONFIG_PATH = Path.home() / ".config" / "kde-hub" / "config.toml"
LOGO_PATH = Path(__file__).parent / "assets" / "icon.png"
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config.toml"
COLORS = {WARN: "#e0a030", CRIT: "#e04040"}
# Tray menu label -> shell script run inside Konsole. sudo needs a real terminal, so the
# app never runs these itself. "Update all" uses `yay -Sua` (AUR only) because pacman already ran.
UPDATE_SCRIPTS = {
    "Update system (pacman -Syu)": "sudo pacman -Syu",
    "Update AUR + system (yay -Syu)": "yay -Syu",
    "Update npm globals (npm update -g)": "npm update -g",
    "Update all": "sudo pacman -Syu && yay -Sua && npm update -g",
}


def konsole_argv(script: str) -> list[str]:
    """Konsole command line that runs `script` and keeps the window open afterwards."""
    return ["konsole", "--hold", "-e", "bash", "-c", script]


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else DEFAULT_CONFIG
    with open(path, "rb") as f:
        return tomllib.load(f)


class _Signals(QObject):
    done = Signal(str, list)


class _Job(QRunnable):
    def __init__(self, module, cfg, signals):
        super().__init__()
        self.module, self.cfg, self.signals = module, cfg, signals

    def run(self):
        self.signals.done.emit(self.module.__name__.rsplit(".", 1)[-1],
                               safe_read(self.module, self.cfg))


def render_section(readings: list[Reading]) -> str:
    rows = []
    for r in readings:
        color = COLORS.get(r.level)
        label, value = html.escape(r.label), html.escape(r.value)  # values come from the network and subprocesses
        value = f'<span style="color:{color}">{value}</span>' if color else value
        rows.append(f"<tr><td style='padding-right:12px'><i>{label}</i></td><td>{value}</td></tr>")
    return f"<table>{''.join(rows)}</table>"


def tray_icon(text: str, level: str) -> QIcon:
    """The KDE logo with the pending-update count in a badge colored by the worst reading level."""
    pix = QPixmap(str(LOGO_PATH)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(COLORS.get(level, "#2e9e5b")))
    p.setPen(QColor("white"))
    p.drawEllipse(26, 26, 38, 38)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(20 if len(text) < 3 else 15)
    p.setFont(font)
    p.drawText(26, 26, 38, 38, Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(pix)


class Hub(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.setWindowTitle("KDE Hub")
        self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.config = config
        self.modules = discover(config)
        self.next_run = {m.__name__: 0.0 for m in self.modules}
        self.running: set[str] = set()
        self.last: dict[str, list[Reading]] = {}
        self.pool = QThreadPool.globalInstance()
        self.signals = _Signals()
        self.signals.done.connect(self.on_result)

        content = QWidget()
        layout = QVBoxLayout(content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.sections: dict[str, QLabel] = {}
        for m in self.modules:
            key = m.__name__.rsplit(".", 1)[-1]
            title = QLabel(f"<b>{m.NAME}</b>")
            body = QLabel("…")
            body.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(body)
            self.sections[key] = body
        layout.addStretch()

        self.tray = QSystemTrayIcon(tray_icon("…", "ok"), self)
        menu = QMenu()
        show = QAction("Show / hide", menu)
        show.triggered.connect(self.toggle)
        quit_ = QAction("Quit", menu)
        quit_.triggered.connect(QApplication.quit)
        menu.addAction(show)
        menu.addSeparator()
        for label, script in UPDATE_SCRIPTS.items():
            action = QAction(label, menu)
            action.triggered.connect(lambda _checked=False, script=script: self.run_in_terminal(script))
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.toggle() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(500)

    def run_in_terminal(self, script: str):
        try:
            subprocess.Popen(konsole_argv(script), start_new_session=True)
        except OSError as err:
            self.tray.showMessage("KDE Hub", f"Could not start konsole: {err}",
                                  QSystemTrayIcon.MessageIcon.Critical)

    def toggle(self):
        self.setVisible(not self.isVisible())
        if self.isVisible():
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def tick(self):
        now = time.monotonic()
        for m in self.modules:
            key = m.__name__.rsplit(".", 1)[-1]
            if key in self.running or now < self.next_run[m.__name__]:
                continue
            self.running.add(key)
            self.next_run[m.__name__] = now + m.INTERVAL
            self.pool.start(_Job(m, monitor_cfg(self.config, key), self.signals))

    def on_result(self, key: str, readings: list[Reading]):
        self.running.discard(key)
        self.last[key] = readings
        self.sections[key].setText(render_section(readings))
        self.update_tray()

    def update_tray(self):
        pending = pending_updates(self.last)
        worst = CRIT if any(r.level == CRIT for rs in self.last.values() for r in rs) else \
            WARN if any(r.level == WARN for rs in self.last.values() for r in rs) else "ok"
        if pending is not None:
            self.tray.setIcon(tray_icon("99+" if pending > 99 else str(pending), worst))
        self.tray.setToolTip("\n".join(f"{k}: " + ", ".join(f"{r.label} {r.value}" for r in rs)
                                       for k, rs in self.last.items()))


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    hub = Hub(load_config())
    app.aboutToQuit.connect(lambda: hub.pool.waitForDone(5000))  # no signals into a deleted Hub
    hub.resize(380, 720)
    if "--show" in sys.argv:
        hub.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

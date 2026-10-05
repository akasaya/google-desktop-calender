"""配布したexe自身で、描画と予定取得を確認する。予定本文は保存しない。"""

import json
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from .storage import save_private


def attach_smoke_report(window, report: Path) -> None:
    timer = QTimer(window)
    deadline = QTimer(window)
    deadline.setSingleShot(True)

    def finish(success: bool):
        timer.stop()
        deadline.stop()
        save_private(
            report,
            json.dumps(
                {
                    "success": success,
                    "mode": "demo" if window.demo else "live",
                    "event_count": len(window.events) if success else 0,
                    "config_dir": str(window.root),
                    "qt_platform": QGuiApplication.platformName(),
                }
            ),
        )
        window.close()

    def check():
        if window.worker is not None:
            return
        if window.loaded:
            finish(True)
        elif "読み込んで" not in window.message.text():
            finish(False)

    timer.timeout.connect(check)
    deadline.timeout.connect(lambda: finish(False))
    timer.start(500)
    deadline.start(90_000)

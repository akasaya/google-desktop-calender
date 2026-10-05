"""GUI起動と取得を確認する。実予定は出力・撮影しない。"""

import argparse
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from google_desktop_calendar.storage import config_dir
from google_desktop_calendar.window import CalendarWindow

parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true")
parser.add_argument("--screenshot", type=Path)
args = parser.parse_args()
if args.live and args.screenshot:
    parser.error("実予定のスクリーンショットは保存しません")

app = QApplication([])
with tempfile.TemporaryDirectory() as temporary:
    window = CalendarWindow(config_dir() if args.live else Path(temporary), demo=not args.live)
    window.show()
    result = [1]

    def check():
        if window.loaded and window.worker is None:
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(args.screenshot)):
                    print("Screenshot failed")
                    window.close()
                    return
            print(f"GUI ready; mode={'live' if args.live else 'demo'}; events={len(window.events)}")
            result[0] = 0
            window.close()
        elif (
            window.worker is None
            and not window.loaded
            and "読み込んで" not in window.message.text()
        ):
            print("GUI fetch failed:", window.message.text())
            window.close()

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(1000)
    QTimer.singleShot(180_000, window.close)
    app.exec()
    raise SystemExit(result[0])

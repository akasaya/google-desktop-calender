"""Windows上で、Python不要の単体exeをビルドする。"""

# invokes this environment's Python with fixed arguments.
import subprocess  # nosec B404
import sys
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

if sys.platform != "win32":
    raise SystemExit(
        "Windows環境、またはGitHub ActionsのWindows EXEワークフローで実行してください。"
    )

root = Path(__file__).resolve().parents[1]
build = root / "build"
build.mkdir(exist_ok=True)
app = QApplication([])
canvas = QImage(256, 256, QImage.Format.Format_ARGB32)
canvas.fill(0)
painter = QPainter(canvas)
QSvgRenderer(str(root / "assets/calendar.svg")).render(painter, QRectF(0, 0, 256, 256))
painter.end()
icon = build / "calendar.ico"
if not canvas.save(str(icon), "ICO"):
    raise SystemExit("アイコンの作成に失敗しました。")

# no shell; all paths derive from this checked-out project.
subprocess.run(  # nosec B603
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "GoogleDesktopCalendar",
        "--icon",
        str(icon),
        "--add-data",
        f"{root / 'assets/calendar.svg'}:assets",
        "--collect-data",
        "tzdata",
        "--copy-metadata",
        "google-auth-oauthlib",
        "--distpath",
        str(root / "dist"),
        "--workpath",
        str(build / "pyinstaller"),
        "--specpath",
        str(build),
        str(root / "scripts/windows_entry.py"),
    ],
    cwd=root,
    check=True,
)

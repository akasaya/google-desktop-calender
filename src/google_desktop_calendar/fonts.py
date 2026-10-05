from pathlib import Path

from PySide6.QtGui import QFontDatabase


def load_japanese_font() -> None:
    """日本語フォントのないWSLgでは、ホストの游ゴシックを直接使用する。"""
    if QFontDatabase.families(QFontDatabase.WritingSystem.Japanese):
        return
    for name in ("YuGothR.ttc", "YuGothB.ttc"):
        font = Path("/mnt/c/Windows/Fonts") / name
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))

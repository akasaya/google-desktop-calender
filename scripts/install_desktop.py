"""Linux/WSLgのアプリ一覧に、このチェックアウトを登録する。"""

import os
from pathlib import Path


def desktop_quote(value: str) -> str:
    # Desktop Entryの文字列とExecでのエスケープを適用する。
    value = value.replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    return '"' + value.replace("\\", "\\\\") + '"'


root = Path(__file__).resolve().parents[1]
python = root / ".venv/bin/python"
if not python.is_file():
    raise SystemExit("先に uv sync --locked --dev を実行してください。")
destination = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
destination.mkdir(parents=True, exist_ok=True)
entry = destination / "google-desktop-calendar.desktop"
entry.write_text(
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=Google Desktop Calendar\n"
    "Name[ja]=今日の予定\n"
    "Comment=Googleカレンダーの今日の予定\n"
    f"Exec={desktop_quote(str(python))} -m google_desktop_calendar\n"
    f"Icon={root / 'assets/calendar.svg'}\n"
    "Terminal=false\n"
    "Categories=Office;Calendar;\n"
    "StartupNotify=true\n",
    encoding="utf-8",
)
entry.chmod(0o644)
print(f"アプリ一覧に登録しました: {entry}")

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

from platformdirs import user_config_path

from .protection import dpapi


def config_dir() -> Path:
    return Path(os.environ.get("GDC_CONFIG_DIR", user_config_path("google-desktop-calendar")))


def save_private(path: Path, text: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_settings(root: Path) -> dict:
    try:
        result = json.loads((root / "settings.json").read_text())
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def save_token(path: Path, text: str) -> None:
    if sys.platform == "win32":
        text = json.dumps(
            {
                "protection": "dpapi-v1",
                "data": base64.b64encode(dpapi(text.encode("utf-8"))).decode("ascii"),
            }
        )
    save_private(path, text)


def load_token(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("認証情報の形式が正しくありません。")
    if "protection" in data:
        if data["protection"] != "dpapi-v1" or sys.platform != "win32":
            raise ValueError("この認証情報は保存したWindowsユーザーでのみ利用できます。")
        cleartext = dpapi(base64.b64decode(data["data"], validate=True), decrypt=True)
        result = json.loads(cleartext.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("認証情報の形式が正しくありません。")
        return result
    if sys.platform == "win32":
        # 書き込みが完了してから置換する。暗号化失敗時に平文へ戻さない。
        save_token(path, json.dumps(data))
    return data

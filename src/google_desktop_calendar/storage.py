import json
import os
import tempfile
from pathlib import Path

from platformdirs import user_config_path


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

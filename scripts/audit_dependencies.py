"""OS条件に関係なくuv.lockの全レジストリ依存を脆弱性照合する。"""

# this Python runs pip-audit with fixed arguments.
import subprocess  # nosec B404
import sys
import tempfile
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lock = tomllib.loads((root / "uv.lock").read_text())
packages = [p for p in lock["package"] if "registry" in p["source"]]
with tempfile.TemporaryDirectory() as directory:
    requirements = Path(directory) / "requirements.txt"
    requirements.write_text("".join(f"{p['name']}=={p['version']}\n" for p in packages))
    # no shell, no installation or dependency resolution.
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pip_audit", "--no-deps", "--disable-pip", "-r", str(requirements)],
        check=False,
    )
    raise SystemExit(result.returncode)

"""Git履歴の秘密情報パターンとCI固定を検査する。値は出力しない。"""

import re

# only fixed, read-only git commands.
import subprocess  # nosec B404
from pathlib import Path

PATTERNS = [
    rb"ya29\.[A-Za-z0-9_-]{10,}",
    rb"GOCSPX-[A-Za-z0-9_-]{10,}",
    rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----",
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb'"(?:access_token|refresh_token|client_secret)"\s*:\s*"[^"\s]{20,}"',
]


def git(*args: str) -> bytes:
    # fixed read-only git arguments.
    return subprocess.check_output(["git", *args])  # nosec B603, B607


def main() -> int:
    failures = []
    count = 0
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        sha, _, name = line.partition(" ")
        if git("cat-file", "-t", sha).strip() != b"blob":
            continue
        count += 1
        data = git("cat-file", "blob", sha)
        if any(re.search(pattern, data) for pattern in PATTERNS):
            failures.append(f"秘密情報の疑い: {name}")
    tracked = git("ls-files", "-z").decode().split("\0")
    for name in filter(None, tracked):
        if re.search(r"(^|/)(token[^/]*\.json|client_secret[^/]*\.json|\.env(?:\..*)?)$", name):
            failures.append(f"認証ファイルの追跡: {name}")
    for workflow in Path(".github/workflows").glob("*.yml"):
        for action in re.findall(r"uses:\s*([^\s#]+)", workflow.read_text()):
            if not re.fullmatch(r"[^@]+@[a-f0-9]{40}", action):
                failures.append(f"ActionsのSHA未固定: {workflow.name}")
    print(f"Git履歴: {count} blobs、指摘: {len(failures)}")
    for failure in failures:
        print(failure)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())

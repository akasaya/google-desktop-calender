import platform
import shutil

# fixed command, URL passed through stdin without a shell.
import subprocess  # nosec B404
import webbrowser
from pathlib import Path

from .security import allowed_url


class BrowserOpenError(Exception):
    """URLを含めずに伝える、ブラウザ起動エラー。"""


def open_browser(url: str) -> bool:
    if not allowed_url(url, auth=True):
        raise BrowserOpenError("Google公式の認証URL以外は開けません。")
    if "microsoft" in platform.release().lower():
        powershell = shutil.which("powershell.exe") or (
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        )
        if not Path(powershell).is_file():
            raise BrowserOpenError(
                "Windowsのブラウザを開けません。WSLの相互運用設定を確認してください。"
            )
        try:
            # URLはコマンドに埋め込まず、標準入力からデータとして渡す。
            # fixed PowerShell code; URL is data on stdin.
            subprocess.run(  # nosec B603
                [
                    powershell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$ErrorActionPreference = 'Stop'; "
                    "$url = [Console]::In.ReadToEnd(); Start-Process -FilePath $url",
                ],
                input=url,
                text=True,
                capture_output=True,
                timeout=15,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise BrowserOpenError(
                "Windowsのブラウザを開けませんでした。WSLの相互運用設定を確認してください。"
            ) from exc
        return True
    try:
        controller = webbrowser.get()
        if isinstance(controller, AuthBrowser):
            raise webbrowser.Error("No system browser")
        opened = controller.open(url, new=1, autoraise=True)
    except webbrowser.Error:
        opened = False
    if not opened:
        raise BrowserOpenError("ブラウザを開けませんでした。OSの既定ブラウザを設定してください。")
    return True


class AuthBrowser:
    def open(self, url: str, new: int = 0, autoraise: bool = True) -> bool:
        return open_browser(url)


def register_auth_browser() -> str:
    name = "google-desktop-calendar-auth"
    # 既定ブラウザを書き換えず、このアプリのOAuth処理だけに使用する。
    webbrowser.register(name, None, AuthBrowser())
    return name

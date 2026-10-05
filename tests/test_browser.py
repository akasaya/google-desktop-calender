import subprocess
from unittest.mock import MagicMock

import pytest

from google_desktop_calendar import browser


@pytest.fixture
def windows_browser(monkeypatch):
    monkeypatch.setattr(browser.platform, "release", lambda: "6.18-microsoft-standard-WSL2")
    monkeypatch.setattr(browser.shutil, "which", lambda _: "/windows/powershell.exe")
    monkeypatch.setattr(browser.Path, "is_file", lambda _: True)
    run = MagicMock()
    monkeypatch.setattr(browser.subprocess, "run", run)
    native = MagicMock()
    monkeypatch.setattr(browser.webbrowser, "open", native)
    return run, native


def test_wsl_opens_host_browser_without_interpolating_url(windows_browser):
    run, native = windows_browser
    url = "https://accounts.google.com/o/oauth2/auth?state=test&value='$(example)'"
    assert browser.open_browser(url)
    command = run.call_args.args[0]
    assert command[0] == "/windows/powershell.exe"
    assert url not in " ".join(command)
    assert run.call_args.kwargs["input"] == url
    assert run.call_args.kwargs["check"] is True
    assert run.call_args.kwargs["timeout"] == 15
    assert not run.call_args.kwargs.get("shell", False)
    native.assert_not_called()


@pytest.mark.parametrize(
    "error", [OSError("private-url"), subprocess.TimeoutExpired("private-url", 15)]
)
def test_wsl_failure_is_prompt_and_does_not_disclose_url(windows_browser, error):
    run, _ = windows_browser
    run.side_effect = error
    with pytest.raises(browser.BrowserOpenError, match="Windows") as caught:
        browser.open_browser("https://accounts.google.com/o/oauth2/auth")
    assert "private-url" not in str(caught.value)


def test_native_browser_failure_is_reported(monkeypatch):
    monkeypatch.setattr(browser.platform, "release", lambda: "linux")
    controller = MagicMock()
    controller.open.return_value = False
    monkeypatch.setattr(browser.webbrowser, "get", lambda: controller)
    with pytest.raises(browser.BrowserOpenError, match="既定ブラウザ"):
        browser.open_browser("https://accounts.google.com/o/oauth2/auth")


def test_missing_system_browser_does_not_recurse(monkeypatch):
    monkeypatch.setattr(browser.platform, "release", lambda: "linux")
    monkeypatch.setattr(browser.webbrowser, "get", lambda: browser.AuthBrowser())
    with pytest.raises(browser.BrowserOpenError, match="既定ブラウザ"):
        browser.open_browser("https://accounts.google.com/o/oauth2/auth")


def test_registered_controller_uses_app_launcher(monkeypatch):
    opened = MagicMock(return_value=True)
    monkeypatch.setattr(browser, "open_browser", opened)
    controller = browser.webbrowser.get(browser.register_auth_browser())
    assert controller.open("https://accounts.google.com/o/oauth2/auth", new=1, autoraise=True)
    opened.assert_called_once_with("https://accounts.google.com/o/oauth2/auth")

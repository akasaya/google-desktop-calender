import json
import sys
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import MismatchingStateError

from google_desktop_calendar import storage
from google_desktop_calendar.calendar import SCOPES, CalendarClient, CalendarError
from google_desktop_calendar.security import allowed_url


@pytest.mark.parametrize(
    "url",
    [
        "https://calendar.google.com/calendar/event?eid=example",
        "https://www.google.com/calendar/event?eid=example",
    ],
)
def test_google_calendar_urls_allowed(url):
    assert allowed_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://calendar.google.com/calendar/",
        "https://calendar.google.com.evil.example/calendar/",
        "https://calendar.google.com@evil.example/calendar/",
        "https://www.google.com/url?q=https://evil.example",
        "https://calendar.google.com:444/calendar/",
        "https://[broken",
        "https://calendar.google.com/calendar/\n",
        "https://evil.example/calendar/",
    ],
)
def test_untrusted_links_are_rejected(url):
    assert not allowed_url(url)


@pytest.mark.parametrize("field", ["auth_uri", "token_uri"])
def test_untrusted_oauth_endpoint_rejected_before_network(
    monkeypatch, tmp_path, client_secret, field
):
    config = json.loads(client_secret.read_text())
    config["installed"][field] = "https://evil.example/oauth"
    client_secret.write_text(json.dumps(config))
    factory = MagicMock()
    monkeypatch.setattr(
        "google_desktop_calendar.calendar.InstalledAppFlow.from_client_config", factory
    )
    with pytest.raises(CalendarError, match="Google公式"):
        CalendarClient(tmp_path).login(client_secret)
    factory.assert_not_called()


def test_oauth_produces_pkce_and_unpredictable_state(client_secret):
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret, SCOPES, autogenerate_code_verifier=True
    )
    flow.redirect_uri = "http://127.0.0.1:12345/"
    url, state = flow.authorization_url()
    query = parse_qs(urlsplit(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) == 43
    assert len(state) >= 20
    assert query["state"] == [state]


def test_oauth_rejects_mismatched_state_before_token_request(monkeypatch, client_secret):
    flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
    flow.redirect_uri = "http://127.0.0.1:12345/"
    flow.authorization_url()
    request = MagicMock()
    monkeypatch.setattr(flow.oauth2session, "request", request)
    with pytest.raises(MismatchingStateError):
        flow.fetch_token(authorization_response="https://127.0.0.1:12345/?code=test&state=wrong")
    request.assert_not_called()


def test_encryption_failure_does_not_overwrite_existing_token(monkeypatch, tmp_path):
    path = tmp_path / "token.json"
    path.write_text('{"test": "preserve"}')
    original = path.read_bytes()
    monkeypatch.setattr(storage.sys, "platform", "win32")

    def fail(_):
        raise OSError("unavailable")

    monkeypatch.setattr(storage, "dpapi", fail)
    with pytest.raises(OSError):
        storage.load_token(path)
    assert path.read_bytes() == original


@pytest.mark.skipif(sys.platform != "win32", reason="実際のWindows DPAPIが必要")
def test_real_windows_dpapi_migrates_and_detects_tampering(tmp_path):
    path = tmp_path / "token.json"
    marker = "test-only-sensitive-value"
    path.write_text(json.dumps({"test": marker}))
    assert storage.load_token(path) == {"test": marker}
    stored = path.read_text()
    assert marker not in stored
    assert json.loads(stored)["protection"] == "dpapi-v1"
    assert storage.load_token(path) == {"test": marker}
    data = json.loads(stored)
    data["data"] = "AAAA"
    path.write_text(json.dumps(data))
    with pytest.raises(OSError):
        storage.load_token(path)

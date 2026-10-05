from datetime import date
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from requests import Timeout

from google_desktop_calendar.calendar import CalendarClient, CalendarError


def event(title, start, end, **extra):
    return {"summary": title, "start": {"dateTime": start}, "end": {"dateTime": end}, **extra}


@pytest.fixture
def api(monkeypatch, tmp_path):
    client = CalendarClient(tmp_path)
    monkeypatch.setattr(client, "credentials", lambda: object())
    session = MagicMock()
    session.__enter__.return_value = session
    monkeypatch.setattr("google_desktop_calendar.calendar.AuthorizedSession", lambda _: session)
    return client, session


def response(data, status=200):
    result = MagicMock()
    result.status_code = status
    result.json.return_value = data
    return result


def test_query_pages_recurring_overlap_and_cancelled(api):
    client, session = api
    session.get.side_effect = [
        response(
            {
                "items": [
                    event("前日から", "2026-10-04T23:00:00+09:00", "2026-10-05T01:00:00+09:00"),
                    event("境界外", "2026-10-04T22:00:00+09:00", "2026-10-05T00:00:00+09:00"),
                    {"status": "cancelled"},
                ],
                "nextPageToken": "page2",
            }
        ),
        response(
            {
                "items": [
                    {
                        "summary": "終日",
                        "start": {"date": "2026-10-05"},
                        "end": {"date": "2026-10-06"},
                    },
                    event("定例", "2026-10-05T12:00:00+09:00", "2026-10-05T13:00:00+09:00"),
                ]
            }
        ),
    ]
    results = client.events(date(2026, 10, 5), ZoneInfo("Asia/Tokyo"), "shared@example.com")
    assert [item.title for item in results] == ["終日", "前日から", "定例"]
    assert session.get.call_count == 2
    args, kwargs = session.get.call_args
    assert "shared%40example.com" in args[0]
    assert kwargs["params"]["timeMin"] == "2026-10-05T00:00:00+09:00"
    assert kwargs["params"]["timeMax"] == "2026-10-06T00:00:00+09:00"
    assert kwargs["params"]["singleEvents"] == "true"
    assert kwargs["params"]["pageToken"] == "page2"
    assert kwargs["timeout"] == 25


@pytest.mark.parametrize("status", [401, 403, 404])
def test_api_errors_do_not_expose_response(api, status):
    client, session = api
    session.get.return_value = response({"secret": "sensitive"}, status)
    with pytest.raises(CalendarError) as error:
        client.events(date(2026, 10, 5), ZoneInfo("Asia/Tokyo"))
    assert "sensitive" not in str(error.value)


def test_timeout_is_actionable(api):
    client, session = api
    session.get.side_effect = Timeout("private-url")
    with pytest.raises(CalendarError, match="通信できません"):
        client.events(date(2026, 10, 5), ZoneInfo("Asia/Tokyo"))


def test_missing_credentials_asks_for_login(tmp_path):
    with pytest.raises(CalendarError, match="Googleに接続"):
        CalendarClient(tmp_path).credentials()


def test_refreshes_and_persists_expired_credentials(monkeypatch, tmp_path):
    creds = MagicMock()
    creds.valid = False
    creds.refresh_token = "test-only"
    creds.to_json.return_value = '{"test": true}'
    monkeypatch.setattr(
        "google_desktop_calendar.calendar.Credentials.from_authorized_user_file", lambda _: creds
    )
    assert CalendarClient(tmp_path).credentials() is creds
    creds.refresh.assert_called_once()
    assert (tmp_path / "token.json").read_text() == '{"test": true}'


def test_revoked_refresh_token_requests_reauthentication(monkeypatch, tmp_path):
    from google.auth.exceptions import RefreshError

    creds = MagicMock()
    creds.valid = False
    creds.refresh.side_effect = RefreshError("private provider details")
    monkeypatch.setattr(
        "google_desktop_calendar.calendar.Credentials.from_authorized_user_file", lambda _: creds
    )
    with pytest.raises(CalendarError, match="再接続") as error:
        CalendarClient(tmp_path).credentials()
    assert "private" not in str(error.value)
    assert not (tmp_path / "token.json").exists()


def test_login_uses_loopback_and_saves_only_after_success(monkeypatch, tmp_path):
    flow = MagicMock()
    flow.client_type = "installed"
    flow.run_local_server.return_value.to_json.return_value = '{"test": true}'
    factory = MagicMock(return_value=flow)
    monkeypatch.setattr(
        "google_desktop_calendar.calendar.InstalledAppFlow.from_client_secrets_file", factory
    )
    CalendarClient(tmp_path).login(tmp_path / "client.json")
    assert factory.call_args.args[1] == ["https://www.googleapis.com/auth/calendar.readonly"]
    assert flow.run_local_server.call_args.kwargs["host"] == "127.0.0.1"
    assert flow.run_local_server.call_args.kwargs["port"] == 0
    assert flow.run_local_server.call_args.kwargs["timeout_seconds"] == 180
    assert (tmp_path / "token.json").is_file()

import json
from datetime import date
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from requests import RequestException

from .models import Event, day_bounds
from .storage import save_private

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarError(Exception):
    """ユーザーに安全に表示できるエラー。"""


class CalendarClient:
    def __init__(self, root: Path):
        self.root = root

    def credentials(self) -> Credentials:
        try:
            creds = Credentials.from_authorized_user_file(str(self.root / "token.json"))
        except (OSError, ValueError, KeyError) as exc:
            raise CalendarError("「Googleに接続」からログインしてください。") from exc
        if not creds.valid:
            if not creds.refresh_token:
                raise CalendarError("認証の有効期限が切れました。Googleに再接続してください。")
            try:
                creds.refresh(Request())
                save_private(self.root / "token.json", creds.to_json())
            except RefreshError as exc:
                raise CalendarError("認証を更新できません。Googleに再接続してください。") from exc
        return creds

    def login(self, secret_path: Path) -> None:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
            if flow.client_type != "installed":
                raise CalendarError(
                    "デスクトップアプリ用のOAuthクライアントJSONを選択してください。"
                )
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=True,
                timeout_seconds=180,
                authorization_prompt_message="ブラウザでGoogleへの接続を完了してください。",
                success_message="接続しました。このタブを閉じてアプリに戻ってください。",
            )
            save_private(self.root / "token.json", creds.to_json())
        except CalendarError:
            raise
        except Exception as exc:
            raise CalendarError(
                "接続できませんでした。OAuth設定を確認して再試行してください。"
            ) from exc

    def events(self, day: date, zone: ZoneInfo, calendar_id: str = "primary") -> list[Event]:
        start, end = day_bounds(day, zone)
        params = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "timeZone": str(zone),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 2500,
        }
        events = []
        try:
            with AuthorizedSession(self.credentials()) as session:
                while True:
                    response = session.get(
                        "https://www.googleapis.com/calendar/v3/calendars/"
                        + quote(calendar_id, safe="")
                        + "/events",
                        params=params,
                        timeout=25,
                    )
                    if response.status_code in (401, 403):
                        raise CalendarError(
                            "アクセスできません。APIの有効化・共有権限・認証を確認してください。"
                        )
                    if response.status_code == 404:
                        raise CalendarError(
                            "カレンダーが見つかりません。カレンダーIDを確認してください。"
                        )
                    response.raise_for_status()
                    data = response.json()
                    for item in data.get("items", []):
                        if item.get("status") == "cancelled":
                            continue
                        event = Event.from_api(item, zone)
                        if event.start < end and event.end > start:
                            events.append(event)
                    token = data.get("nextPageToken")
                    if not token:
                        break
                    params["pageToken"] = token
        except (RequestException, RefreshError) as exc:
            raise CalendarError("通信できません。接続を確認して「更新」を押してください。") from exc
        return sorted(events, key=lambda event: (not event.all_day, event.start, event.title))

    def import_mcp(self, tokens_path: Path, secret_path: Path, account: str) -> None:
        """明示指定された既存認証をコピーする。元ファイルは変更しない。"""
        tokens = json.loads(tokens_path.read_text())[account]
        secret = json.loads(secret_path.read_text())["installed"]
        creds = Credentials(
            token=tokens.get("access_token"),
            refresh_token=tokens["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=secret["client_id"],
            client_secret=secret["client_secret"],
        )
        creds.refresh(Request())
        save_private(self.root / "token.json", creds.to_json())

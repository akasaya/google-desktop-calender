from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from google_desktop_calendar.models import Event, day_bounds

TOKYO = ZoneInfo("Asia/Tokyo")


def test_day_bounds_handle_daylight_saving():
    start, end = day_bounds(date(2026, 3, 8), ZoneInfo("America/New_York"))
    assert (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() == 23 * 3600
    assert start.hour == end.hour == 0


def test_all_day_end_is_exclusive():
    event = Event.from_api({"start": {"date": "2026-10-05"}, "end": {"date": "2026-10-06"}}, TOKYO)
    assert event.title == "（タイトルなし）"
    assert event.all_day
    assert event.end == datetime(2026, 10, 6, tzinfo=TOKYO)
    assert event.time_label(date(2026, 10, 5)) == "終日"


def test_utc_event_converts_to_local_day_and_status():
    event = Event.from_api(
        {
            "summary": "打ち合わせ",
            "start": {"dateTime": "2026-10-04T23:00:00Z"},
            "end": {"dateTime": "2026-10-05T00:00:00Z"},
        },
        TOKYO,
    )
    assert event.start == datetime(2026, 10, 5, 8, tzinfo=TOKYO)
    assert event.status(datetime(2026, 10, 5, 7, tzinfo=TOKYO)) == "これから"
    assert event.status(event.start) == "進行中"
    assert event.status(event.end) == "終了"


def test_cross_day_label():
    event = Event(
        "夜間", datetime(2026, 10, 4, 23, tzinfo=TOKYO), datetime(2026, 10, 5, 1, tzinfo=TOKYO)
    )
    assert event.time_label(date(2026, 10, 5)) == "10/04 23:00 – 01:00"

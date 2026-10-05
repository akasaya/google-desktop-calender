import threading
from datetime import datetime, timedelta

from PySide6.QtWidgets import QLabel

from google_desktop_calendar.calendar import CalendarError
from google_desktop_calendar.models import demo_events
from google_desktop_calendar.window import CalendarWindow


def test_demo_renders_cards(qtbot, tmp_path):
    window = CalendarWindow(tmp_path, demo=True)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.loaded)
    assert "5件の予定" in window.summary.text()
    assert "デモ" in window.message.text()
    assert any(item.text() == "朝のプランニング" for item in window.findChildren(QLabel))


def test_async_fetch_and_failure_preserve_previous_events(qtbot, tmp_path):
    class Client:
        fail = False

        def events(self, day, zone, calendar_id):
            assert threading.current_thread() is not threading.main_thread()
            if self.fail:
                raise CalendarError("通信できません")
            return demo_events(day, zone)

    client = Client()
    window = CalendarWindow(tmp_path, client=client)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.loaded and window.worker is None)
    client.fail = True
    window.refresh()
    qtbot.waitUntil(lambda: window.worker is None)
    assert len(window.events) == 5
    assert "前回取得" in window.message.text()
    assert window.refresh_button.isEnabled()


def test_empty_calendar_is_success(qtbot, tmp_path):
    class Client:
        def events(self, *_):
            return []

    window = CalendarWindow(tmp_path, client=Client())
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.loaded and window.worker is None)
    assert "同期済み" in window.message.text()
    assert any(item.text() == "今日は予定がありません" for item in window.findChildren(QLabel))


def test_midnight_clears_previous_day_before_failed_refresh(qtbot, tmp_path):
    class Client:
        def events(self, *_):
            raise CalendarError("オフライン")

    window = CalendarWindow(tmp_path, demo=True, client=Client())
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.loaded)
    window.demo = False
    window.day = datetime.now(window.zone).date() - timedelta(days=1)
    window.tick()
    qtbot.waitUntil(lambda: window.worker is None)
    assert not window.events
    assert not window.loaded
    assert "前回取得" not in window.message.text()


def test_close_waits_for_worker(qtbot, tmp_path):
    release = threading.Event()

    class Client:
        def events(self, *_):
            release.wait(timeout=2)
            return []

    window = CalendarWindow(tmp_path, client=Client())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.worker is not None)
    window.close()
    assert window.isVisible()
    release.set()
    qtbot.waitUntil(lambda: not window.isVisible())


def test_manual_refresh_after_midnight_drops_stale_events(qtbot, tmp_path):
    class Client:
        def events(self, *_):
            raise CalendarError("オフライン")

    window = CalendarWindow(tmp_path, demo=True, client=Client())
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.loaded)
    window.demo = False
    window.day -= timedelta(days=1)
    window.refresh()
    qtbot.waitUntil(lambda: window.worker is None)
    assert not window.events
    assert not window.loaded


def test_previous_day_result_does_not_replace_current_day(qtbot, tmp_path):
    window = CalendarWindow(tmp_path, demo=True)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window.loaded)
    yesterday = window.day - timedelta(days=1)
    window.requested_day = yesterday
    window.received(demo_events(yesterday, window.zone))
    assert not window.events
    assert not window.loaded

import json

from google_desktop_calendar.smoke import attach_smoke_report
from google_desktop_calendar.window import CalendarWindow


def test_smoke_report_verifies_gui_without_recording_event_details(qtbot, tmp_path):
    window = CalendarWindow(tmp_path / "config", demo=True)
    qtbot.addWidget(window)
    report = tmp_path / "report.json"
    attach_smoke_report(window, report)
    window.show()
    qtbot.waitUntil(report.is_file, timeout=3000)
    result = json.loads(report.read_text())
    assert result["success"] is True
    assert result["event_count"] == 5
    assert result["mode"] == "demo"
    assert set(result) == {"success", "mode", "event_count", "config_dir", "qt_platform"}
    assert not window.isVisible()

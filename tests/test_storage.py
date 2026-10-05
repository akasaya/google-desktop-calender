import os
import stat

from google_desktop_calendar.storage import load_settings, save_private


def test_atomic_private_storage(tmp_path):
    path = tmp_path / "config" / "token.json"
    save_private(path, "first")
    save_private(path, "second")
    assert path.read_text() == "second"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(path.parent.iterdir()) == [path]


def test_invalid_settings_fall_back(tmp_path):
    assert load_settings(tmp_path) == {}
    (tmp_path / "settings.json").write_text("invalid")
    assert load_settings(tmp_path) == {}

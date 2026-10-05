import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .calendar import CalendarClient, CalendarError
from .fonts import load_japanese_font
from .models import Event, demo_events
from .security import allowed_url
from .storage import load_settings, save_private

STYLE = """
QMainWindow, QDialog { background: #101827; }
QWidget { color: #e5edf8; font-family: 'Noto Sans CJK JP', 'Yu Gothic', 'Yu Gothic UI', sans-serif;
          font-size: 14px; }
QLabel { background: transparent; }
QLabel#brand { color: #80dfc4; font-size: 12px; font-weight: 700; }
QLabel#date { font-size: 30px; font-weight: 700; }
QLabel#muted { color: #99a9be; }
QLabel#title { font-size: 17px; font-weight: 600; }
QLabel#status { color: #80dfc4; }
QFrame#card { background: #1b283c; border: 1px solid #2a3b54; border-radius: 14px; }
QFrame#active { background: #163731; border: 1px solid #53b69c; border-radius: 14px; }
QPushButton { background: #25364e; border: 1px solid #354a65; border-radius: 8px;
              padding: 9px 14px; }
QPushButton:hover { background: #314864; }
QPushButton:disabled { color: #758196; }
QPushButton#primary { background: #80dfc4; color: #102c26; font-weight: 700; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #101827; width: 8px; }
QScrollBar::handle:vertical { background: #3b506a; border-radius: 4px; min-height: 24px; }
QLineEdit { background: #1b283c; border: 1px solid #354a65; padding: 9px; border-radius: 6px; }
QCheckBox { padding: 8px; }
"""


def label(text: str, name: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


class Worker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.succeeded.emit(self.action())
        except CalendarError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("読み込みに失敗しました。設定を確認して再試行してください。")


class SettingsDialog(QDialog):
    def __init__(self, calendar_id: str, timezone: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("表示設定")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)
        self.calendar = QLineEdit(calendar_id)
        self.timezone = QLineEdit(timezone)
        layout.addRow("カレンダーID", self.calendar)
        layout.addRow("タイムゾーン", self.timezone)
        layout.addRow(label("通常は primary / Asia/Tokyo を使用します。", "muted"))
        self.error = label("")
        layout.addRow(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def validate(self):
        try:
            ZoneInfo(self.timezone.text().strip())
            if not self.calendar.text().strip():
                raise ValueError
        except (ValueError, ZoneInfoNotFoundError):
            self.error.setText("カレンダーIDと有効なタイムゾーンを入力してください。")
            return
        self.accept()


class CalendarWindow(QMainWindow):
    def __init__(self, root: Path, demo: bool = False, client=None):
        super().__init__()
        load_japanese_font()
        self.root = root
        self.demo = demo
        self.client = client or CalendarClient(root)
        settings = load_settings(root)
        try:
            self.zone = ZoneInfo(str(settings.get("timezone", "Asia/Tokyo")))
        except (ValueError, ZoneInfoNotFoundError):
            self.zone = ZoneInfo("Asia/Tokyo")
        self.calendar_id = str(settings.get("calendar_id", "primary"))
        self.day = datetime.now(self.zone).date()
        self.events: list[Event] = []
        self.worker: Worker | None = None
        self.loaded = False
        self.closing = False
        self.setWindowTitle("今日の予定 · Google Desktop Calendar")
        self.resize(600, 800)
        self.setMinimumSize(480, 520)
        self.setStyleSheet(STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 28, 28, 22)
        layout.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("TODAY / GOOGLE CALENDAR", "brand"))
        top.addStretch()
        self.clock = label("", "muted")
        top.addWidget(self.clock)
        layout.addLayout(top)
        self.date_label = label("", "date")
        layout.addWidget(self.date_label)
        self.summary = label("今日の予定を、ひと目で。", "muted")
        layout.addWidget(self.summary)
        toolbar = QHBoxLayout()
        self.refresh_button = QPushButton("更新")
        self.refresh_button.setObjectName("primary")
        self.refresh_button.clicked.connect(self.refresh)
        self.login_button = QPushButton("Googleに接続")
        self.login_button.clicked.connect(self.login)
        self.settings_button = QPushButton("設定")
        self.settings_button.clicked.connect(self.settings)
        for button in (self.refresh_button, self.login_button, self.settings_button):
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.message = label("", "status")
        layout.addWidget(self.message)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_widget.setObjectName("eventList")
        self.list_widget.setStyleSheet("QWidget#eventList { background: transparent; }")
        self.cards = QVBoxLayout(self.list_widget)
        self.cards.setContentsMargins(0, 0, 8, 0)
        self.cards.setSpacing(12)
        self.cards.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)
        footer = QHBoxLayout()
        self.pin = QCheckBox("常に手前")
        self.pin.toggled.connect(self.toggle_pin)
        footer.addWidget(self.pin)
        footer.addStretch()
        self.zone_label = label(f"{self.zone} · 5分ごとに更新", "muted")
        footer.addWidget(self.zone_label)
        layout.addLayout(footer)
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start(30_000)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(300_000)
        self.tick()
        QTimer.singleShot(0, self.refresh)

    @Slot(bool)
    def toggle_pin(self, enabled: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()

    @Slot()
    def tick(self):
        now = datetime.now(self.zone)
        self.clock.setText(now.strftime("%H:%M"))
        self.date_label.setText(
            f"{now.month}月{now.day}日  {('月火水木金土日')[now.weekday()]}曜日"
        )
        if now.date() != self.day:
            self.day = now.date()
            self.events = []
            self.loaded = False
            self.render()
            self.refresh()
        elif self.loaded:
            self.render()

    def busy(self, value: bool):
        for button in (self.refresh_button, self.login_button, self.settings_button):
            button.setEnabled(not value)

    def start_worker(self, action, on_success):
        self.busy(True)
        self.worker = Worker(action, self)
        self.worker.succeeded.connect(on_success)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    @Slot()
    def finished(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
        self.busy(False)
        if self.closing:
            self.close()
        elif getattr(self, "requested_day", self.day) != self.day or getattr(
            self, "after_login", False
        ):
            self.after_login = False
            self.refresh()

    @Slot(str)
    def failed(self, message: str):
        suffix = "（前回取得した予定を表示中）" if self.loaded else ""
        self.message.setText(message + suffix)
        if not self.loaded:
            self.render()

    @Slot()
    def refresh(self):
        if self.worker is not None or self.closing:
            return
        today = datetime.now(self.zone).date()
        if today != self.day:
            self.day = today
            self.events = []
            self.loaded = False
            self.render()
        self.requested_day = self.day
        self.message.setText("予定を読み込んでいます…")
        if self.demo:
            self.received(demo_events(self.day, self.zone))
        else:
            day, zone, calendar_id = self.day, self.zone, self.calendar_id
            self.start_worker(lambda: self.client.events(day, zone, calendar_id), self.received)

    @Slot(object)
    def received(self, events):
        if self.requested_day != datetime.now(self.zone).date():
            self.day = datetime.now(self.zone).date()
            self.events = []
            self.loaded = False
            self.render()
            return
        self.events = events
        self.loaded = True
        now = datetime.now(self.zone)
        self.message.setText(
            "デモ表示 · サンプルの予定です" if self.demo else f"同期済み · {now:%H:%M}"
        )
        self.render()

    def render(self):
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        now = datetime.now(self.zone)
        remaining = sum(not event.all_day and event.end > now for event in self.events)
        self.summary.setText(
            f"{len(self.events)}件の予定 · このあとの予定 {remaining}件"
            if self.loaded
            else "今日の予定を、ひと目で。"
        )
        if not self.events:
            title = "今日は予定がありません" if self.loaded else "Google カレンダーとつながる"
            detail = (
                "ゆとりのある一日を。"
                if self.loaded
                else "「Googleに接続」から、今日の予定を表示しましょう。"
            )
            card = QFrame()
            card.setObjectName("card")
            box = QVBoxLayout(card)
            box.setContentsMargins(24, 32, 24, 32)
            box.addWidget(label(title, "title"))
            box.addWidget(label(detail, "muted"))
            self.cards.addWidget(card)
        for event in self.events:
            card = QFrame()
            status = event.status(now)
            card.setObjectName("active" if status == "進行中" else "card")
            box = QVBoxLayout(card)
            box.setContentsMargins(20, 16, 20, 16)
            row = QHBoxLayout()
            row.addWidget(label(event.time_label(self.day), "status"))
            row.addStretch()
            row.addWidget(label(status, "muted"))
            box.addLayout(row)
            box.addWidget(label(event.title, "title"))
            if event.location:
                box.addWidget(label(event.location, "muted"))
            if allowed_url(event.url):
                button = QPushButton("カレンダーで開く ↗")
                button.clicked.connect(
                    lambda checked=False, url=event.url: QDesktopServices.openUrl(QUrl(url))
                )
                box.addWidget(button, alignment=Qt.AlignmentFlag.AlignRight)
            self.cards.addWidget(card)

    @Slot()
    def login(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Google OAuth クライアントJSONを選択", "", "JSON (*.json)"
        )
        if path:
            self.message.setText("ブラウザで接続してください（3分以内）。")
            self.start_worker(lambda: self.client.login(Path(path)), self.logged_in)

    @Slot(object)
    def logged_in(self, _):
        self.demo = False
        self.after_login = True
        self.events = []
        self.loaded = False
        self.render()

    @Slot()
    def settings(self):
        dialog = SettingsDialog(self.calendar_id, str(self.zone), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            calendar_id = dialog.calendar.text().strip()
            timezone = dialog.timezone.text().strip()
            try:
                save_private(
                    self.root / "settings.json",
                    json.dumps(
                        {
                            "calendar_id": calendar_id,
                            "timezone": timezone,
                        }
                    ),
                )
            except OSError:
                self.message.setText("設定を保存できません。保存先の権限を確認してください。")
                return
            self.calendar_id = calendar_id
            self.zone = ZoneInfo(timezone)
            self.day = datetime.now(self.zone).date()
            self.events = []
            self.loaded = False
            self.zone_label.setText(f"{self.zone} · 5分ごとに更新")
            self.tick()
            self.render()
            self.refresh()

    def closeEvent(self, event: QCloseEvent):
        if self.worker is not None:
            self.closing = True
            self.message.setText("通信の終了を待っています…")
            self.refresh_timer.stop()
            self.tick_timer.stop()
            event.ignore()
        else:
            event.accept()

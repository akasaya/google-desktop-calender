from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    return datetime.combine(day, time.min, zone), datetime.combine(
        day + timedelta(days=1), time.min, zone
    )


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    location: str = ""
    url: str = ""

    @classmethod
    def from_api(cls, item: dict, zone: ZoneInfo) -> "Event":
        all_day = "date" in item["start"]

        def parse(value: dict) -> datetime:
            if "date" in value:
                return datetime.combine(date.fromisoformat(value["date"]), time.min, zone)
            result = datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00"))
            if result.tzinfo is None:
                result = result.replace(tzinfo=ZoneInfo(value.get("timeZone", str(zone))))
            return result.astimezone(zone)

        return cls(
            title=item.get("summary") or "（タイトルなし）",
            start=parse(item["start"]),
            end=parse(item["end"]),
            all_day=all_day,
            location=item.get("location", ""),
            url=item.get("htmlLink", ""),
        )

    def status(self, now: datetime) -> str:
        if self.all_day:
            return "終日"
        if self.end <= now:
            return "終了"
        if self.start <= now:
            return "進行中"
        return "これから"

    def time_label(self, day: date) -> str:
        if self.all_day:
            return "終日"
        start = self.start.strftime("%H:%M" if self.start.date() == day else "%m/%d %H:%M")
        end = self.end.strftime("%H:%M" if self.end.date() == day else "%m/%d %H:%M")
        return f"{start} – {end}"


def demo_events(day: date, zone: ZoneInfo) -> list[Event]:
    start, end = day_bounds(day, zone)
    return [
        Event("プロジェクトを進める日", start, end, all_day=True),
        Event("朝のプランニング", start.replace(hour=9), start.replace(hour=9, minute=30)),
        Event(
            "集中して開発",
            start.replace(hour=10),
            start.replace(hour=12),
            location="ワークスペース",
        ),
        Event(
            "チームミーティング",
            start.replace(hour=14),
            start.replace(hour=15),
            location="オンライン",
        ),
        Event("一日の振り返り", start.replace(hour=17), start.replace(hour=17, minute=30)),
    ]

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, tz).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, tz).astimezone(UTC),
    )


def local_day_of(moment: datetime, tz: ZoneInfo) -> date:
    if moment.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")
    return moment.astimezone(tz).date()

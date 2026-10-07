import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_timezone() -> ZoneInfo:
    name = os.getenv("APP_TZ", "Asia/Almaty")
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError, IsADirectoryError) as exc:
        raise ValueError(f"Invalid APP_TZ: {name!r}") from exc

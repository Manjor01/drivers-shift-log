import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domain import Trip
from app.timeutil import day_bounds


class TripConflict(Exception):
    pass


class TripRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS trips "
                "(id TEXT PRIMARY KEY, start_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS trips_start ON trips(start_at, id)")

    def add(self, trip: Trip) -> bool:
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            cursor = db.execute(
                "INSERT INTO trips VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING",
                (trip.id, trip.start_at.isoformat(timespec="microseconds"), trip.model_dump_json()),
            )
            if cursor.rowcount == 1:
                return True
            row = db.execute("SELECT payload FROM trips WHERE id = ?", (trip.id,)).fetchone()
            if row is None or Trip.model_validate_json(row[0]) != trip:
                raise TripConflict(trip.id)
            return False

    def for_day(self, day: date, tz: ZoneInfo) -> list[Trip]:
        start, end = day_bounds(day, tz)
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT payload FROM trips WHERE start_at >= ? AND start_at < ? "
                "ORDER BY start_at, id",
                (start.isoformat(timespec="microseconds"), end.isoformat(timespec="microseconds")),
            ).fetchall()
        return [Trip.model_validate_json(row[0]) for row in rows]

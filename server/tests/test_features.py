from concurrent.futures import ThreadPoolExecutor
from datetime import date
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.domain import Trip
from app.main import create_app
from app.storage import TripRepository
from app.summary import compute_summary
from app.timeutil import day_bounds

PAYLOAD = dict(
    id="t1",
    start="2026-10-01T08:10:00+05:00",
    end="2026-10-01T08:32:00+05:00",
    amount=2400,
    payment="card",
    commission=360,
)


def trip() -> Trip:
    return Trip.model_validate(
        dict(
            id="t1",
            start_at=PAYLOAD["start"],
            end_at=PAYLOAD["end"],
            amount=2400,
            payment_method="card",
            commission=360,
        )
    )


def test_summary():
    cash = trip().model_copy(
        update=dict(id="t2", amount=1500, commission=225, payment_method="cash")
    )
    result = compute_summary(iter([trip(), cash]))
    assert result.total.model_dump() == dict(trip_count=2, revenue=3900, commission=585, net=3315)
    assert result.cash.net == 1275
    assert result.card.net == 2040
    assert compute_summary([]).total.net == 0


def test_dst():
    for day, hours in [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)]:
        start, end = day_bounds(day, ZoneInfo("America/New_York"))
        assert (end - start).total_seconds() == hours * 3600


def test_api(tmp_path):
    db = tmp_path / "trips.db"
    with TestClient(create_app(db_path=db, seed_path=None)) as client:
        assert client.post("/api/trips", json=PAYLOAD).status_code == 201
        assert client.post("/api/trips", json=PAYLOAD).status_code == 200
        normalized = PAYLOAD | dict(start="2026-10-01T03:10:00Z", end="2026-10-01T03:32:00Z")
        assert client.post("/api/trips", json=normalized).status_code == 200
        assert client.post("/api/trips", json=PAYLOAD | dict(amount=2500)).status_code == 409
        assert client.post("/api/trips", json=PAYLOAD | dict(amount=True)).status_code == 422
        assert (
            client.post("/api/trips", json=PAYLOAD | dict(end=PAYLOAD["start"])).status_code == 422
        )
        body = client.get("/api/day?day=2026-10-01").json()
        assert len(body["trips"]) == 1
        assert body["summary"]["total"]["net"] == 2040
        assert client.get("/api/day?day=2026-10-02").json()["trips"] == []
        assert client.get("/api/day?day=bad").status_code == 422
    with TestClient(create_app(db_path=db, seed_path=None)) as client:
        assert len(client.get("/api/day?day=2026-10-01").json()["trips"]) == 1


def test_concurrent_dedup(tmp_path):
    repo = TripRepository(tmp_path / "race.db")
    repo.initialize()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: repo.add(trip()), range(20)))
    assert results.count(True) == 1
    assert len(repo.for_day(date(2026, 10, 1), ZoneInfo("Asia/Almaty"))) == 1


def test_midnight_and_sorting(tmp_path):
    repo = TripRepository(tmp_path / "days.db")
    repo.initialize()
    for payload in [
        PAYLOAD | dict(id="z", start="2026-10-01T23:50:00+05:00", end="2026-10-02T00:20:00+05:00"),
        PAYLOAD | dict(id="a", start="2026-10-01T23:50:00+05:00", end="2026-10-02T00:20:00+05:00"),
        PAYLOAD
        | dict(id="new", start="2026-10-02T00:00:00+05:00", end="2026-10-02T00:20:00+05:00"),
    ]:
        from app.main import TripInput

        repo.add(Trip.model_validate(TripInput.model_validate(payload).model_dump()))
    assert [t.id for t in repo.for_day(date(2026, 10, 1), ZoneInfo("Asia/Almaty"))] == ["a", "z"]
    assert [t.id for t in repo.for_day(date(2026, 10, 2), ZoneInfo("Asia/Almaty"))] == ["new"]


def test_seed_restarts_without_duplicates(tmp_path):
    import json

    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps([PAYLOAD]))
    for _ in range(2):
        with TestClient(create_app(db_path=tmp_path / "seed.db", seed_path=seed)) as client:
            assert (
                client.get("/api/day?day=2026-10-01").json()["summary"]["total"]["trip_count"] == 1
            )


def test_summary_randomized_reference():
    import random

    rng = random.Random(42)
    trips = []
    for i in range(300):
        amount = rng.randrange(1, 1_000_000_000)
        trips.append(
            trip().model_copy(
                update=dict(
                    id=str(i),
                    amount=amount,
                    commission=rng.randrange(amount + 1),
                    payment_method=rng.choice(["cash", "card"]),
                )
            )
        )
    result = compute_summary(iter(trips))
    assert result.total.revenue == sum(t.amount for t in trips)
    assert result.total.commission == sum(t.commission for t in trips)
    assert result.total.net == result.cash.net + result.card.net
    assert result.total.trip_count == 300
    for method in ("cash", "card"):
        bucket = getattr(result, method)
        assert bucket.revenue == sum(t.amount for t in trips if t.payment_method == method)
        assert bucket.commission == sum(t.commission for t in trips if t.payment_method == method)
    rng.shuffle(trips)
    assert compute_summary(trips) == result


def test_timezone_configuration(monkeypatch):
    import pytest

    from app.config import get_timezone

    monkeypatch.delenv("APP_TZ", raising=False)
    assert get_timezone().key == "Asia/Almaty"
    monkeypatch.setenv("APP_TZ", "UTC")
    assert get_timezone().key == "UTC"
    for value in ("", "America", "Not/AZone"):
        monkeypatch.setenv("APP_TZ", value)
        with pytest.raises(ValueError, match="APP_TZ"):
            get_timezone()


def test_almaty_day_and_naive_input():
    from datetime import UTC, datetime

    import pytest

    from app.timeutil import local_day_of

    tz = ZoneInfo("Asia/Almaty")
    start, end = day_bounds(date(2026, 10, 1), tz)
    assert start == datetime(2026, 9, 30, 19, tzinfo=UTC)
    assert end == datetime(2026, 10, 1, 19, tzinfo=UTC)
    assert local_day_of(start, tz) == date(2026, 10, 1)
    assert local_day_of(end, tz) == date(2026, 10, 2)
    with pytest.raises(ValueError):
        local_day_of(datetime(2026, 10, 1), tz)


def test_assignment_seed_contract(tmp_path):
    from pathlib import Path

    seed = Path(__file__).resolve().parents[2] / "data" / "seed.json"
    with TestClient(create_app(db_path=tmp_path / "assignment.db", seed_path=seed)) as client:
        response = client.get("/api/day?day=2026-10-01")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == dict(
            trip_count=2, revenue=3900, commission=585, net=3315
        )
        assert data["summary"]["cash"]["net"] == 1275
        assert data["summary"]["card"]["net"] == 2040
        assert [t["id"] for t in data["trips"]] == ["t1", "t2"]
        assert data["trips"][0]["start"] == "2026-10-01T08:10:00+05:00"


def test_api_rejects_dates_that_can_overflow_utc_boundaries(tmp_path):
    with TestClient(
        create_app(db_path=tmp_path / "date-range.db", seed_path=None),
        raise_server_exceptions=False,
    ) as client:
        for day in ("0001-01-01", "0001-12-31", "9999-01-01", "9999-12-31"):
            response = client.get("/api/day", params={"day": day})
            assert response.status_code == 422
            assert response.json()["detail"][0]["loc"] == ["query", "day"]
        for day in ("0002-01-01", "2026-10-01", "9998-12-31"):
            assert client.get("/api/day", params={"day": day}).status_code == 200

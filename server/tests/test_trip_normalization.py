"""Step 1: timestamps are normalized to UTC; Trip is an immutable value with an id key."""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.domain import Trip


def make(**overrides: Any) -> Trip:
    payload: dict[str, Any] = {
        "id": "t1",
        "start_at": "2026-10-01T08:10:00+05:00",
        "end_at": "2026-10-01T08:32:00+05:00",
        "amount": 2400,
        "payment_method": "card",
        "commission": 360,
    }
    payload.update(overrides)
    return Trip.model_validate(payload)


# ------------------------------------------------------------- UTC conversion


def test_offset_timestamps_are_converted_to_utc() -> None:
    trip = make()
    assert trip.start_at == datetime(2026, 10, 1, 3, 10, tzinfo=UTC)
    assert trip.end_at == datetime(2026, 10, 1, 3, 32, tzinfo=UTC)
    assert trip.start_at.utcoffset() == timedelta(0)
    assert trip.end_at.utcoffset() == timedelta(0)


def test_z_suffix_is_accepted_and_stays_utc() -> None:
    trip = make(start_at="2026-10-01T03:10:00Z", end_at="2026-10-01T03:32:00Z")
    assert trip.start_at == datetime(2026, 10, 1, 3, 10, tzinfo=UTC)
    assert trip.start_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("raw", "expected_utc"),
    [
        ("2026-10-01T08:10:00-07:00", datetime(2026, 10, 1, 15, 10, tzinfo=UTC)),
        ("2026-10-01T08:10:00+05:30", datetime(2026, 10, 1, 2, 40, tzinfo=UTC)),
        ("2026-10-01T08:10:00+05:45", datetime(2026, 10, 1, 2, 25, tzinfo=UTC)),
    ],
    ids=["negative-offset", "half-hour-offset", "45-minute-offset"],
)
def test_other_offsets_are_converted_correctly(raw: str, expected_utc: datetime) -> None:
    trip = make(start_at=raw, end_at=(expected_utc + timedelta(minutes=10)).isoformat())
    assert trip.start_at == expected_utc
    assert trip.start_at.utcoffset() == timedelta(0)


def test_datetime_object_with_named_timezone_is_converted_to_utc() -> None:
    almaty = ZoneInfo("Asia/Almaty")
    trip = make(
        start_at=datetime(2026, 10, 1, 8, 10, tzinfo=almaty),
        end_at=datetime(2026, 10, 1, 8, 32, tzinfo=almaty),
    )
    assert trip.start_at == datetime(2026, 10, 1, 3, 10, tzinfo=UTC)
    assert trip.start_at.utcoffset() == timedelta(0)


def test_microseconds_are_preserved() -> None:
    trip = make(start_at="2026-10-01T08:10:00.123456+05:00", end_at="2026-10-01T08:32:00+05:00")
    assert trip.start_at.microsecond == 123456


def test_normalization_can_change_the_calendar_date() -> None:
    """00:30 local on Oct 1 is Sep 30 in UTC; the model applies no business-day rule."""
    trip = make(start_at="2026-10-01T00:30:00+05:00", end_at="2026-10-01T01:00:00+05:00")
    assert trip.start_at == datetime(2026, 9, 30, 19, 30, tzinfo=UTC)


def test_other_fields_are_not_modified_by_normalization() -> None:
    trip = make()
    assert (trip.id, trip.amount, trip.payment_method, trip.commission) == ("t1", 2400, "card", 360)


# --------------------------------------------------- value semantics and identity


def test_same_instant_in_different_offsets_gives_equal_trips() -> None:
    local = make()
    utc = make(start_at="2026-10-01T03:10:00Z", end_at="2026-10-01T03:32:00Z")
    assert local == utc
    assert hash(local) == hash(utc)


def test_identical_trips_collapse_in_a_set() -> None:
    assert len({make(), make()}) == 1


def test_same_id_with_different_data_is_not_equal_but_shares_the_identity_key() -> None:
    original = make()
    changed = make(amount=2500)
    assert original.id == changed.id
    assert original != changed


def test_different_id_with_same_data_is_a_different_trip() -> None:
    assert make(id="t1") != make(id="t2")


def test_trip_is_immutable() -> None:
    trip = make()
    with pytest.raises(ValidationError):
        trip.amount = 1  # type: ignore[misc]

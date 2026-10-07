"""Step 1: expected validation behaviour of the Trip domain model.

Expectations are written as literals on purpose: they define the contract
independently of how the implementation names its constants.
"""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain import Trip


def valid_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "t1",
        "start_at": "2026-10-01T08:10:00+05:00",
        "end_at": "2026-10-01T08:32:00+05:00",
        "amount": 2400,
        "payment_method": "card",
        "commission": 360,
    }
    payload.update(overrides)
    return payload


def without(*fields: str, **overrides: Any) -> dict[str, Any]:
    payload = valid_payload(**overrides)
    for field in fields:
        del payload[field]
    return payload


def error_locs(payload: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Validate a payload that must be rejected and return where it failed."""
    with pytest.raises(ValidationError) as exc_info:
        Trip.model_validate(payload)
    return sorted(error["loc"] for error in exc_info.value.errors())


def assert_rejected_at(payload: dict[str, Any], field: str) -> None:
    assert error_locs(payload) == [(field,)]


# ---------------------------------------------------------------- valid input


def test_first_sample_trip_from_the_assignment_is_valid() -> None:
    trip = Trip.model_validate(valid_payload())
    assert trip.id == "t1"
    assert trip.amount == 2400
    assert trip.commission == 360
    assert trip.payment_method == "card"


def test_second_sample_trip_from_the_assignment_is_valid() -> None:
    trip = Trip.model_validate(
        {
            "id": "t2",
            "start_at": "2026-10-01T09:05:00+05:00",
            "end_at": "2026-10-01T09:20:00+05:00",
            "amount": 1500,
            "payment_method": "cash",
            "commission": 225,
        }
    )
    assert trip.payment_method == "cash"
    assert trip.amount == 1500


@pytest.mark.parametrize("commission", [0, 2400], ids=["zero", "equal-to-amount"])
def test_commission_boundaries_are_valid(commission: int) -> None:
    assert Trip.model_validate(valid_payload(commission=commission)).commission == commission


@pytest.mark.parametrize("amount", [1, 1_000_000_000], ids=["minimum", "maximum"])
def test_amount_boundaries_are_valid(amount: int) -> None:
    assert Trip.model_validate(valid_payload(amount=amount, commission=0)).amount == amount


def test_one_second_trip_is_valid() -> None:
    Trip.model_validate(valid_payload(end_at="2026-10-01T08:10:01+05:00"))


def test_exactly_24_hour_trip_is_valid() -> None:
    Trip.model_validate(valid_payload(end_at="2026-10-02T08:10:00+05:00"))


def test_trip_crossing_midnight_is_valid() -> None:
    Trip.model_validate(
        valid_payload(start_at="2026-10-01T23:50:00+05:00", end_at="2026-10-02T00:20:00+05:00")
    )


@pytest.mark.parametrize(
    "trip_id",
    ["t1", "a" * 64, "trip-2026.10:01_A", "7"],
    ids=["simple", "64-chars", "allowed-punctuation", "digit-only"],
)
def test_valid_ids(trip_id: str) -> None:
    assert Trip.model_validate(valid_payload(id=trip_id)).id == trip_id


@pytest.mark.parametrize("method", ["cash", "card"])
def test_valid_payment_methods(method: str) -> None:
    assert Trip.model_validate(valid_payload(payment_method=method)).payment_method == method


def test_aware_datetime_objects_are_accepted_in_python_construction() -> None:
    from datetime import UTC

    trip = Trip.model_validate(
        valid_payload(
            start_at=datetime(2026, 10, 1, 3, 10, tzinfo=UTC),
            end_at=datetime(2026, 10, 1, 3, 32, tzinfo=UTC),
        )
    )
    assert trip.end_at > trip.start_at


# ------------------------------------------------------------- invalid amount


@pytest.mark.parametrize(
    "amount",
    [0, -1, 1.5, 2400.0, "2400", True, False, None, 1_000_000_001],
    ids=[
        "zero",
        "negative",
        "fractional",
        "float-with-integer-value",
        "numeric-string",
        "true",
        "false",
        "null",
        "above-maximum",
    ],
)
def test_invalid_amount_is_rejected(amount: Any) -> None:
    assert_rejected_at(valid_payload(amount=amount, commission=0), "amount")


def test_missing_amount_is_rejected() -> None:
    assert_rejected_at(without("amount", commission=0), "amount")


# --------------------------------------------------------- invalid commission


@pytest.mark.parametrize(
    "commission",
    [-1, 2401, 1.5, 360.0, "360", True, None],
    ids=[
        "negative",
        "greater-than-amount",
        "fractional",
        "float-with-integer-value",
        "numeric-string",
        "true",
        "null",
    ],
)
def test_invalid_commission_is_rejected(commission: Any) -> None:
    assert_rejected_at(valid_payload(commission=commission), "commission")


def test_missing_commission_is_rejected() -> None:
    assert_rejected_at(without("commission"), "commission")


def test_commission_is_not_compared_with_an_invalid_amount() -> None:
    """Only the real problem (amount) must be reported, not a spurious commission error."""
    assert_rejected_at(valid_payload(amount=0, commission=100), "amount")


# ---------------------------------------------------------- invalid payment


@pytest.mark.parametrize(
    "method",
    ["CASH", "Cash", "bank", "", None, 1, True, ["cash"]],
    ids=["upper", "capitalized", "unknown", "empty", "null", "int", "bool", "list"],
)
def test_invalid_payment_method_is_rejected(method: Any) -> None:
    assert_rejected_at(valid_payload(payment_method=method), "payment_method")


def test_missing_payment_method_is_rejected() -> None:
    assert_rejected_at(without("payment_method"), "payment_method")


# ------------------------------------------------------------- invalid times

BAD_TIMESTAMPS: list[Any] = [
    "2026-10-01T08:10:00",
    "2026-10-01",
    "yesterday",
    "",
    None,
    1_790_000_000,
    1_790_000_000.5,
    True,
    "1790000000",
    datetime(2026, 10, 1, 8, 10),
]
BAD_TIMESTAMP_IDS = [
    "no-offset",
    "date-only",
    "garbage",
    "empty",
    "null",
    "unix-int",
    "unix-float",
    "bool",
    "unix-numeric-string",
    "naive-datetime-object",
]


@pytest.mark.parametrize("value", BAD_TIMESTAMPS, ids=BAD_TIMESTAMP_IDS)
def test_invalid_start_at_is_rejected(value: Any) -> None:
    assert_rejected_at(valid_payload(start_at=value), "start_at")


@pytest.mark.parametrize("value", BAD_TIMESTAMPS, ids=BAD_TIMESTAMP_IDS)
def test_invalid_end_at_is_rejected(value: Any) -> None:
    assert_rejected_at(valid_payload(end_at=value), "end_at")


@pytest.mark.parametrize("field", ["start_at", "end_at"])
def test_missing_timestamp_is_rejected(field: str) -> None:
    assert_rejected_at(without(field), field)


# ------------------------------------------------------------ time ordering


def test_end_equal_to_start_is_rejected() -> None:
    assert_rejected_at(valid_payload(end_at="2026-10-01T08:10:00+05:00"), "end_at")


def test_end_before_start_is_rejected() -> None:
    assert_rejected_at(valid_payload(end_at="2026-10-01T08:09:59+05:00"), "end_at")


def test_multiday_trip_is_valid() -> None:
    Trip.model_validate(valid_payload(end_at="2026-10-03T08:10:01+05:00"))


def test_ordering_uses_instants_not_wall_clock_time() -> None:
    """Wall clock says end (04:00) < start (08:00), but in UTC end 04:00Z is after 03:00Z."""
    Trip.model_validate(
        valid_payload(start_at="2026-10-01T08:00:00+05:00", end_at="2026-10-01T04:00:00+00:00")
    )


def test_ordering_uses_instants_even_when_wall_clock_looks_later() -> None:
    """Wall clock says end (09:00) > start (08:00), but end 04:00Z is before start 08:00Z."""
    assert_rejected_at(
        valid_payload(start_at="2026-10-01T08:00:00+00:00", end_at="2026-10-01T09:00:00+05:00"),
        "end_at",
    )


def test_end_is_not_compared_with_an_invalid_start() -> None:
    assert_rejected_at(valid_payload(start_at="garbage"), "start_at")


# ----------------------------------------------------------------- invalid id


@pytest.mark.parametrize(
    "trip_id",
    ["", " ", " t1", "t1 ", "t 1", "t/1", "t1\n", "a" * 65, "т1", 123, True, None],
    ids=[
        "empty",
        "spaces-only",
        "leading-space",
        "trailing-space",
        "inner-space",
        "slash",
        "trailing-newline",
        "65-chars",
        "cyrillic",
        "int",
        "bool",
        "null",
    ],
)
def test_invalid_id_is_rejected(trip_id: Any) -> None:
    assert_rejected_at(valid_payload(id=trip_id), "id")


def test_missing_id_is_rejected() -> None:
    assert_rejected_at(without("id"), "id")


# --------------------------------------------------------------- extra fields


def test_unknown_field_is_rejected() -> None:
    assert_rejected_at(valid_payload(driver_id="d1"), "driver_id")


# ------------------------------------------------------------ many errors


def test_independent_errors_are_all_reported() -> None:
    payload = valid_payload(id="bad id", amount=-5, payment_method="bank", commission=0)
    assert error_locs(payload) == [("amount",), ("id",), ("payment_method",)]


def test_empty_payload_reports_every_required_field() -> None:
    expected = [("amount",), ("commission",), ("end_at",), ("id",), ("payment_method",)]
    assert error_locs({}) == sorted(expected + [("start_at",)])

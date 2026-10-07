"""Validated, immutable trip values. No persistence or HTTP dependencies."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class Trip(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[
        str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    ]
    start_at: datetime
    end_at: datetime
    amount: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]
    payment_method: Literal["cash", "card"]
    commission: Annotated[int, Field(strict=True, ge=0)]

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def aware_utc(cls, value: Any) -> datetime:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Expected an ISO-8601 timestamp with timezone") from exc
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Expected a timezone-aware timestamp")
        return value.astimezone(UTC)

    @field_validator("end_at")
    @classmethod
    def ordered(cls, value: datetime, info: ValidationInfo) -> datetime:
        start = info.data.get("start_at")
        if start is not None and value <= start:
            raise ValueError("end_at must be later than start_at")
        return value

    @field_validator("commission")
    @classmethod
    def bounded_commission(cls, value: int, info: ValidationInfo) -> int:
        amount = info.data.get("amount")
        if amount is not None and value > amount:
            raise ValueError("commission must not exceed amount")
        return value

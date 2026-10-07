from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, computed_field

from app.domain import Trip


class Totals(BaseModel):
    model_config = ConfigDict(frozen=True)
    trip_count: int = 0
    revenue: int = 0
    commission: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def net(self) -> int:
        return self.revenue - self.commission


class Summary(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: Totals
    cash: Totals
    card: Totals


def compute_summary(trips: Iterable[Trip]) -> Summary:
    buckets = {"cash": [0, 0, 0], "card": [0, 0, 0]}
    for trip in trips:
        row = buckets[trip.payment_method]
        row[0] += 1
        row[1] += trip.amount
        row[2] += trip.commission

    def totals(row: list[int]) -> Totals:
        return Totals(trip_count=row[0], revenue=row[1], commission=row[2])

    return Summary(
        total=totals([a + b for a, b in zip(buckets["cash"], buckets["card"], strict=True)]),
        cash=totals(buckets["cash"]),
        card=totals(buckets["card"]),
    )

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_timezone
from app.domain import Trip
from app.storage import TripConflict, TripRepository
from app.summary import Summary, compute_summary


class TripInput(Trip):
    id: Annotated[
        str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    ]
    start_at: datetime = Field(alias="start")
    end_at: datetime = Field(alias="end")
    payment_method: Literal["cash", "card"] = Field(alias="payment")


class TripOutput(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    start: datetime
    end: datetime
    amount: int
    payment: Literal["cash", "card"]
    commission: int


class DayOutput(BaseModel):
    day: date
    timezone: str
    summary: Summary
    trips: list[TripOutput]


def create_app(
    db_path: Path | None = None, seed_path: Path | None = Path("data/seed.json")
) -> FastAPI:
    repo = TripRepository(db_path or Path(os.getenv("DB_PATH", "data/trips.db")))
    tz = get_timezone()

    def output(trip: Trip) -> TripOutput:
        return TripOutput(
            id=trip.id,
            start=trip.start_at.astimezone(tz),
            end=trip.end_at.astimezone(tz),
            amount=trip.amount,
            payment=trip.payment_method,
            commission=trip.commission,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        repo.initialize()
        seed = Path(os.getenv("SEED_PATH", str(seed_path))) if seed_path is not None else None
        if seed is not None and seed.exists():
            for payload in json.loads(seed.read_text()):
                value = TripInput.model_validate(payload)
                repo.add(Trip.model_validate(value.model_dump()))
        yield

    application = FastAPI(title="Driver Shift Diary", lifespan=lifespan)

    @application.get("/api/day", response_model=DayOutput)
    def get_day(
        day: Annotated[
            date,
            Query(
                ge=date(2, 1, 1),
                le=date(9998, 12, 31),
                description="Local day between 0002-01-01 and 9998-12-31",
            ),
        ],
    ) -> DayOutput:
        trips = repo.for_day(day, tz)
        return DayOutput(
            day=day,
            timezone=tz.key,
            summary=compute_summary(trips),
            trips=[output(t) for t in trips],
        )

    @application.post("/api/trips", response_model=TripOutput, status_code=201)
    def add_trip(payload: TripInput, response: Response) -> TripOutput:
        trip = Trip.model_validate(payload.model_dump())
        try:
            created = repo.add(trip)
        except TripConflict as exc:
            raise HTTPException(409, "A trip with this id already has different data") from exc
        response.status_code = 201 if created else 200
        return output(trip)

    return application


app = create_app()

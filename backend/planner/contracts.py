from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class DutyStatus(StrEnum):
    OFF = "OFF"
    SB = "SB"
    D = "D"
    ON = "ON"


class EventKind(StrEnum):
    DRIVE = "drive"
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    FUEL = "fuel"
    BREAK = "break"
    DAILY_REST = "daily_rest"
    CYCLE_RESTART = "cycle_restart"


@dataclass(frozen=True)
class Location:
    id: str
    label: str
    longitude: float
    latitude: float
    timezone: str

    @property
    def coordinate(self) -> tuple[float, float]:
        return self.longitude, self.latitude


@dataclass(frozen=True)
class LogMetadata:
    driver_name: str | None = None
    carrier_name: str | None = None
    carrier_address: str | None = None
    truck_number: str | None = None
    trailer_number: str | None = None
    shipment_reference: str | None = None
    starting_odometer_miles: Decimal | None = None


@dataclass(frozen=True)
class TripRequest:
    current_location: Location
    pickup_location: Location
    dropoff_location: Location
    cycle_used_hours: Decimal
    departure_at: datetime
    log_timezone: str
    metadata: LogMetadata


@dataclass(frozen=True)
class DutyEvent:
    id: str
    kind: EventKind
    status: DutyStatus
    start_at: datetime
    end_at: datetime
    start_location: Location
    end_location: Location
    distance_m: int = 0
    driving_leg_id: str | None = None
    reasons: tuple[str, ...] = ()
    poi_id: str | None = None

    @property
    def duration_s(self) -> int:
        return int((self.end_at - self.start_at).total_seconds())


def to_wire(value):
    """One JSON conversion for all immutable domain records; decimals stay strings."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value):
        return {field.name: to_wire(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): to_wire(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_wire(item) for item in value]
    return value

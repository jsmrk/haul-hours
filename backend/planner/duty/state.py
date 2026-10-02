from dataclasses import dataclass
from datetime import datetime, timezone

from planner.contracts import TripRequest


@dataclass(frozen=True)
class DutyState:
    now: datetime
    window_started_at: datetime | None = None
    daily_drive_s: int = 0
    break_drive_s: int = 0
    cycle_used_s: int = 0
    non_driving_run_s: int = 0
    off_duty_run_s: int = 0
    distance_since_fuel_m: int = 0


def initial_state(request: TripRequest) -> DutyState:
    return DutyState(request.departure_at.astimezone(timezone.utc),
                     cycle_used_s=int(request.cycle_used_hours * 3600))

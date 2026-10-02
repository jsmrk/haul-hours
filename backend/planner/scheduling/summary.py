from dataclasses import dataclass
from datetime import datetime

from planner.contracts import DutyStatus, EventKind
from planner.scheduling.scheduler import ScheduledTrip


@dataclass(frozen=True)
class TripSummary:
    pickup_arrival_at: datetime
    dropoff_arrival_at: datetime
    completed_at: datetime
    distance_m: int
    driving_s: int
    elapsed_s: int
    on_duty_s: int
    off_duty_s: int
    fuel_stop_count: int
    short_break_count: int
    daily_rest_count: int
    cycle_restart_count: int


def summarize_trip(trip: ScheduledTrip) -> TripSummary:
    pickup = next(event for event in trip.events if event.kind == EventKind.PICKUP)
    dropoff = next(event for event in trip.events if event.kind == EventKind.DROPOFF)
    durations = {status: sum(event.duration_s for event in trip.events if event.status == status) for status in DutyStatus}
    counts = {kind: sum(event.kind == kind for event in trip.events) for kind in EventKind}
    return TripSummary(pickup.start_at, dropoff.start_at, dropoff.end_at,
                       sum(event.distance_m for event in trip.events), durations[DutyStatus.D],
                       int((dropoff.end_at - trip.events[0].start_at).total_seconds()),
                       durations[DutyStatus.ON], durations[DutyStatus.OFF] + durations[DutyStatus.SB],
                       counts[EventKind.FUEL], counts[EventKind.BREAK], counts[EventKind.DAILY_REST],
                       counts[EventKind.CYCLE_RESTART])

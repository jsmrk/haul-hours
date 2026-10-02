from datetime import timezone

from planner.constants import (
    BREAK_DRIVE_S, BREAK_S, CYCLE_RESTART_S, CYCLE_S, DAILY_DRIVE_S,
    DAILY_REST_S, DRIVING_WINDOW_S, FUEL_RANGE_M,
)
from planner.contracts import DutyEvent, DutyStatus, EventKind, TripRequest


def audit_timeline(request: TripRequest, events: tuple[DutyEvent, ...]) -> tuple[str, ...]:
    """Independent replay: deliberately does not call state transitions or scheduling helpers."""
    issues = []
    expected = request.departure_at.astimezone(timezone.utc)
    location = request.current_location.coordinate
    daily = since_break = non_driving = off = fuel = 0
    cycle = int(request.cycle_used_hours * 3600)
    window = None
    ids = set()
    for event in events:
        if event.start_at.tzinfo is None or event.end_at.tzinfo is None:
            issues.append(f"{event.id}: timestamps lack timezone")
            continue
        start, end = event.start_at.astimezone(timezone.utc), event.end_at.astimezone(timezone.utc)
        duration = int((end - start).total_seconds())
        if start != expected or event.start_location.coordinate != location:
            issues.append(f"{event.id}: timeline/location continuity broken")
        if duration <= 0 or event.id in ids or event.distance_m < 0:
            issues.append(f"{event.id}: invalid duration, distance, or duplicate ID")
        ids.add(event.id)
        expected, location = end, event.end_location.coordinate
        if event.status in (DutyStatus.D, DutyStatus.ON) and window is None:
            window = start
        if event.status == DutyStatus.D:
            if event.kind != EventKind.DRIVE:
                issues.append(f"{event.id}: driving kind/status mismatch")
            daily += duration
            since_break += duration
            cycle += duration
            fuel += event.distance_m
            if daily > DAILY_DRIVE_S:
                issues.append(f"{event.id}: daily driving limit exceeded")
            if since_break > BREAK_DRIVE_S:
                issues.append(f"{event.id}: break driving limit exceeded")
            if cycle > CYCLE_S:
                issues.append(f"{event.id}: cycle driving availability exceeded")
            if window is not None and (end - window).total_seconds() > DRIVING_WINDOW_S:
                issues.append(f"{event.id}: driving window exceeded")
            if fuel > FUEL_RANGE_M:
                issues.append(f"{event.id}: fuel range exceeded")
            non_driving = off = 0
        else:
            if event.distance_m != 0 or event.start_location.coordinate != event.end_location.coordinate:
                issues.append(f"{event.id}: non-driving event changes road location")
            non_driving += duration
            off = off + duration if event.status in (DutyStatus.OFF, DutyStatus.SB) else 0
            if event.status == DutyStatus.ON:
                cycle += duration
            if non_driving >= BREAK_S:
                since_break = 0
            if off >= DAILY_REST_S:
                daily, window = 0, None
            if off >= CYCLE_RESTART_S:
                cycle = 0
            if event.kind == EventKind.FUEL:
                if event.status != DutyStatus.ON or duration < BREAK_S:
                    issues.append(f"{event.id}: fuel requires 30 minutes on duty")
                fuel = 0
    return tuple(issues)

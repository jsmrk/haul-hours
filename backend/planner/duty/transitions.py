from dataclasses import replace
from datetime import timezone

from planner.constants import BREAK_S, CYCLE_RESTART_S, DAILY_REST_S, FUEL_RANGE_M
from planner.contracts import DutyEvent, DutyStatus, EventKind
from planner.duty.limits import driving_allowance
from planner.duty.state import DutyState
from planner.errors import PlanningProblem


def apply_event(state: DutyState, event: DutyEvent) -> DutyState:
    seconds = event.duration_s
    if event.start_at.tzinfo is None or event.end_at.tzinfo is None:
        raise PlanningProblem("INVALID_TIMELINE", "Duty events must have timezone-aware timestamps.")
    if event.start_at != state.now or seconds <= 0 or event.distance_m < 0:
        raise PlanningProblem("INVALID_TIMELINE", "Duty events must be positive and contiguous.")
    if event.status == DutyStatus.D:
        if seconds > driving_allowance(state) or state.distance_since_fuel_m + event.distance_m > FUEL_RANGE_M:
            raise PlanningProblem("DUTY_LIMIT_EXCEEDED", "This driving edge exceeds the available duty or fuel allowance.")
        return replace(state, now=event.end_at.astimezone(timezone.utc),
                       window_started_at=state.window_started_at or state.now,
                       daily_drive_s=state.daily_drive_s + seconds, break_drive_s=state.break_drive_s + seconds,
                       cycle_used_s=state.cycle_used_s + seconds, non_driving_run_s=0, off_duty_run_s=0,
                       distance_since_fuel_m=state.distance_since_fuel_m + event.distance_m)
    non_driving = state.non_driving_run_s + seconds
    off_duty = state.off_duty_run_s + seconds if event.status in (DutyStatus.OFF, DutyStatus.SB) else 0
    window = state.window_started_at
    cycle = state.cycle_used_s
    if event.status == DutyStatus.ON:
        window = window or state.now
        cycle += seconds
    daily_reset = off_duty >= DAILY_REST_S
    return replace(state, now=event.end_at.astimezone(timezone.utc), window_started_at=None if daily_reset else window,
                   daily_drive_s=0 if daily_reset else state.daily_drive_s,
                   break_drive_s=0 if non_driving >= BREAK_S else state.break_drive_s,
                   cycle_used_s=0 if off_duty >= CYCLE_RESTART_S else cycle,
                   non_driving_run_s=non_driving, off_duty_run_s=off_duty,
                   distance_since_fuel_m=0 if event.kind == EventKind.FUEL else state.distance_since_fuel_m)

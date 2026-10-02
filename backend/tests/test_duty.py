from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from planner.contracts import DutyEvent, DutyStatus, EventKind
from planner.duty.audit import audit_timeline
from planner.duty.limits import driving_allowance
from planner.duty.state import initial_state
from planner.duty.transitions import apply_event
from planner.errors import PlanningProblem


def event(state, request, seconds, status=DutyStatus.D, kind=EventKind.DRIVE):
    return DutyEvent(str(state.now), kind, status, state.now, state.now + timedelta(seconds=seconds),
                     request.current_location, request.current_location)


def advance(state, request, seconds, status=DutyStatus.D, kind=EventKind.DRIVE):
    return apply_event(state, event(state, request, seconds, status, kind))


def test_exact_break_boundary_requires_30_minutes(trip_request):
    state = advance(initial_state(trip_request), trip_request, 28800)
    assert driving_allowance(state) == 0
    state = advance(state, trip_request, 1799, DutyStatus.OFF, EventKind.BREAK)
    assert driving_allowance(state) == 0
    state = advance(state, trip_request, 1, DutyStatus.OFF, EventKind.BREAK)
    assert driving_allowance(state) == 10800


def test_adjacent_on_and_off_qualify_for_break_but_not_daily_rest(trip_request):
    state = advance(initial_state(trip_request), trip_request, 28800)
    state = advance(state, trip_request, 900, DutyStatus.ON, EventKind.PICKUP)
    state = advance(state, trip_request, 900, DutyStatus.OFF, EventKind.BREAK)
    assert state.break_drive_s == 0
    assert state.daily_drive_s == 28800
    assert state.cycle_used_s == 29700
    assert state.off_duty_run_s == 900


def test_daily_driving_limit_and_consecutive_reset(trip_request):
    state = advance(initial_state(trip_request), trip_request, 28800)
    state = advance(state, trip_request, 1800, DutyStatus.OFF, EventKind.BREAK)
    state = advance(state, trip_request, 10800)
    assert driving_allowance(state) == 0
    with pytest.raises(PlanningProblem):
        advance(state, trip_request, 1)
    state = advance(state, trip_request, 35999, DutyStatus.OFF, EventKind.DAILY_REST)
    assert state.daily_drive_s == 39600
    state = advance(state, trip_request, 1, DutyStatus.OFF, EventKind.DAILY_REST)
    assert state.daily_drive_s == 0 and state.window_started_at is None
    assert state.cycle_used_s == 39600


def test_short_break_does_not_pause_14_hour_window(trip_request):
    state = advance(initial_state(trip_request), trip_request, 3600, DutyStatus.ON, EventKind.PICKUP)
    state = advance(state, trip_request, 27000, DutyStatus.OFF, EventKind.BREAK)
    assert driving_allowance(state) == 19800
    state = advance(state, trip_request, 19800)
    assert driving_allowance(state) == 0


def test_loading_can_exceed_cycle_but_prohibits_further_driving(trip_request):
    request = replace(trip_request, cycle_used_hours=Decimal("69.50"))
    state = advance(initial_state(request), request, 3600, DutyStatus.ON, EventKind.PICKUP)
    assert state.cycle_used_s == 253800
    assert driving_allowance(state) == 0
    state = advance(state, request, 36000, DutyStatus.OFF, EventKind.DAILY_REST)
    assert driving_allowance(state) == 0
    state = advance(state, request, 86400, DutyStatus.OFF, EventKind.CYCLE_RESTART)
    assert state.cycle_used_s == 0
    assert driving_allowance(state) == 28800


def test_fuel_resets_mileage_and_break_but_not_cycle(trip_request):
    state = replace(initial_state(trip_request), break_drive_s=28800, distance_since_fuel_m=1609344)
    state = advance(state, trip_request, 1800, DutyStatus.ON, EventKind.FUEL)
    assert state.distance_since_fuel_m == 0 and state.break_drive_s == 0
    assert state.cycle_used_s == 1800


def test_midnight_does_not_reset_driving(trip_request):
    request = replace(trip_request, departure_at=trip_request.departure_at.replace(hour=23))
    state = advance(initial_state(request), request, 7200)
    assert state.daily_drive_s == state.break_drive_s == state.cycle_used_s == 7200


def test_elapsed_time_crossing_dst_uses_utc_not_wall_clock(trip_request):
    zone = ZoneInfo("America/New_York")
    start = datetime(2026, 3, 8, 1, 30, tzinfo=zone)
    end = datetime(2026, 3, 8, 3, 30, tzinfo=zone)
    request = replace(trip_request, departure_at=start)
    drive = DutyEvent("dst", EventKind.DRIVE, DutyStatus.D, start, end,
                      request.current_location, request.current_location)
    assert drive.duration_s == 3600
    assert apply_event(initial_state(request), drive).daily_drive_s == 3600


def test_34_hour_restart_requires_every_consecutive_second(trip_request):
    request = replace(trip_request, cycle_used_hours=Decimal("70"))
    state = advance(initial_state(request), request, 122399, DutyStatus.OFF, EventKind.CYCLE_RESTART)
    assert state.cycle_used_s == 252000
    state = advance(state, request, 1, DutyStatus.OFF, EventKind.CYCLE_RESTART)
    assert state.cycle_used_s == 0


def test_independent_audit_rejects_one_second_violation_and_overlap(trip_request):
    state = initial_state(trip_request)
    drive = event(state, trip_request, 28801)
    assert any("break" in issue.lower() for issue in audit_timeline(trip_request, (drive,)))
    second = replace(drive, id="overlap", start_at=drive.end_at - timedelta(seconds=1),
                     end_at=drive.end_at + timedelta(seconds=1))
    assert any("continuity" in issue.lower() for issue in audit_timeline(trip_request, (drive, second)))


def test_final_on_duty_service_is_allowed_after_window_and_cycle(trip_request):
    request = replace(trip_request, cycle_used_hours=Decimal("69"))
    start = request.departure_at
    events = (
        DutyEvent("drive", EventKind.DRIVE, DutyStatus.D, start, start + timedelta(hours=1), request.current_location, request.current_location),
        DutyEvent("wait", EventKind.BREAK, DutyStatus.OFF, start + timedelta(hours=1), start + timedelta(hours=10), request.current_location, request.current_location),
        DutyEvent("unload", EventKind.DROPOFF, DutyStatus.ON, start + timedelta(hours=10), start + timedelta(hours=15), request.current_location, request.current_location),
    )
    assert audit_timeline(request, events) == ()

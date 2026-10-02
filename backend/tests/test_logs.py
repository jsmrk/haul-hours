from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from planner.contracts import DutyEvent, DutyStatus, EventKind
from planner.logs.days import build_daily_logs
from planner.scheduling.scheduler import ScheduledTrip
from tests.network import road


def trip_at(request, start, seconds, status=DutyStatus.D, meters=1000):
    request = replace(request, departure_at=start)
    leg = road(request.current_location, request.dropoff_location, seconds, meters)
    event = DutyEvent("shared-id", EventKind.DRIVE if status == DutyStatus.D else EventKind.CYCLE_RESTART,
                      status, start, start + timedelta(seconds=seconds), request.current_location,
                      request.dropoff_location if status == DutyStatus.D else request.current_location,
                      meters if status == DutyStatus.D else 0, leg.id if status == DutyStatus.D else None)
    return ScheduledTrip(request, (leg,), (event,), ())


def test_midnight_split_conserves_miles_and_event_id(trip_request):
    start = datetime(2026, 10, 3, 3, tzinfo=timezone.utc)  # 23:00 at home terminal
    trip = trip_at(trip_request, start, 7200, meters=1001)
    logs = build_daily_logs(trip)
    assert [log.date for log in logs] == ["2026-10-02", "2026-10-03"]
    assert [log.distance_m for log in logs] == [500, 501]
    assert sum(log.distance_m for log in logs) == 1001
    assert all(sum(log.totals_s.values()) == 86400 for log in logs)
    assert all(log.totals_s[DutyStatus.SB] == 0 for log in logs)
    assert all(any(interval.event_id == "shared-id" for interval in log.intervals) for log in logs)
    assert logs[0].intervals[0].assumed_outside_trip
    assert logs[1].intervals[-1].assumed_outside_trip
    assert trip.events[-1].end_at == start + timedelta(hours=2)


@pytest.mark.parametrize("day,duration,tick_count", [("2026-03-08", 82800, 24), ("2026-11-01", 90000, 26)])
def test_dst_days_have_chronological_axes_with_explicit_offsets(trip_request, day, duration, tick_count):
    local = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo("America/New_York"))
    trip = trip_at(trip_request, local.astimezone(timezone.utc), duration, DutyStatus.OFF, 0)
    log = build_daily_logs(trip)[0]
    assert log.duration_s == sum(log.totals_s.values()) == duration
    assert len(log.graph.ticks) == tick_count
    assert [tick.elapsed_s for tick in log.graph.ticks] == list(range(0, duration + 1, 3600))
    assert "UTC" in log.graph.ticks[1].label
    if day == "2026-11-01":
        assert log.graph.ticks[1].utc_offset_s == -14400 and log.graph.ticks[2].utc_offset_s == -18000


def test_midnight_completion_does_not_add_empty_day(trip_request):
    start = datetime(2026, 10, 3, 3, tzinfo=timezone.utc)
    logs = build_daily_logs(trip_at(trip_request, start, 3600))
    assert len(logs) == 1 and logs[0].date == "2026-10-02"


def test_restart_keeps_whole_off_duty_intermediate_days(trip_request):
    start = datetime(2026, 10, 3, 2, tzinfo=timezone.utc)
    logs = build_daily_logs(trip_at(trip_request, start, 122400, DutyStatus.OFF, 0))
    assert len(logs) == 3
    assert logs[1].totals_s[DutyStatus.OFF] == 86400
    assert not logs[1].intervals[0].assumed_outside_trip
    assert all(0 <= point[0] <= 1 and 0 <= point[1] <= 3 for log in logs for path in log.graph.paths for point in path.points)

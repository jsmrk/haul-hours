from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from planner.contracts import DutyStatus
from planner.errors import PlanningProblem
from planner.logs.contracts import DailyLog, LogInterval, LogRemark
from planner.logs.graph import build_graph
from planner.routing.geometry import distance_at_elapsed
from planner.scheduling.scheduler import ScheduledTrip

OUTSIDE_TRIP = "Assumed off duty outside planned trip"


def build_daily_logs(trip: ScheduledTrip) -> tuple[DailyLog, ...]:
    zone = ZoneInfo(trip.request.log_timezone)
    departure = trip.events[0].start_at.astimezone(timezone.utc)
    completed = trip.events[-1].end_at.astimezone(timezone.utc)
    day = departure.astimezone(zone).date()
    last_day = (completed - timedelta(microseconds=1)).astimezone(zone).date()
    legs = {leg.id: leg for leg in trip.road_legs}
    logs = []
    while day <= last_day:
        if len(logs) >= 365:
            raise PlanningProblem("RESULT_TOO_LARGE", "The trip exceeds the supported daily-sheet count.", 413)
        start = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
        end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
        intervals = []
        remarks = []
        cursor = start
        for event in trip.events:
            event_start = event.start_at.astimezone(timezone.utc)
            event_end = event.end_at.astimezone(timezone.utc)
            left, right = max(start, event_start), min(end, event_end)
            if left >= right:
                continue
            if left > cursor:
                if cursor >= departure:
                    raise PlanningProblem("INVALID_TIMELINE", "A gap exists inside the planned trip.", 503)
                intervals.append(LogInterval(None, DutyStatus.OFF, cursor, left, 0, True))
                remarks.append(LogRemark(cursor, trip.request.current_location.label, OUTSIDE_TRIP, None))
            distance = 0
            if event.driving_leg_id:
                leg = legs[event.driving_leg_id]
                distance = distance_at_elapsed(leg, int((right - event_start).total_seconds())) - distance_at_elapsed(
                    leg, int((left - event_start).total_seconds()))
            intervals.append(LogInterval(event.id, event.status, left, right, distance, False))
            continued = "Continues: " if left > event_start else ""
            note = continued + event.kind.replace("_", " ").title()
            if event.reasons:
                note += ": " + "; ".join(event.reasons)
            location = event.start_location.label if event.status != DutyStatus.D else (
                f"En route: {event.start_location.label} to {event.end_location.label}")
            remarks.append(LogRemark(left, location, note, event.id))
            cursor = right
        if cursor < end:
            if cursor < completed:
                raise PlanningProblem("INVALID_TIMELINE", "A gap exists inside the planned trip.", 503)
            intervals.append(LogInterval(None, DutyStatus.OFF, cursor, end, 0, True))
            remarks.append(LogRemark(cursor, trip.request.dropoff_location.label, OUTSIDE_TRIP, None))
        totals = {status: sum(int((interval.end_at - interval.start_at).total_seconds()) for interval in intervals
                              if interval.status == status) for status in DutyStatus}
        logs.append(DailyLog(day.isoformat(), trip.request.log_timezone, start, end,
                             int((end - start).total_seconds()), tuple(intervals), totals,
                             sum(interval.distance_m for interval in intervals), tuple(remarks),
                             build_graph(start, end, trip.request.log_timezone, tuple(intervals))))
        day += timedelta(days=1)
    return tuple(logs)

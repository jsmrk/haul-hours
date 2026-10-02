from datetime import timedelta
from zoneinfo import ZoneInfo

from planner.contracts import DutyStatus
from planner.logs.contracts import GraphPath, GraphTick, LogGraph, LogInterval


def build_graph(start, end, timezone: str, intervals: tuple[LogInterval, ...]) -> LogGraph:
    duration = int((end - start).total_seconds())
    zone = ZoneInfo(timezone)
    offsets = list(range(0, duration + 1, 3600))
    if offsets[-1] != duration:
        offsets.append(duration)
    ticks = []
    for elapsed in offsets:
        local = (start + timedelta(seconds=elapsed)).astimezone(zone)
        offset = int(local.utcoffset().total_seconds())
        label = "24:00" if elapsed == duration else local.strftime("%H:%M")
        if duration != 86400:
            sign = "+" if offset >= 0 else "-"
            label += f" UTC{sign}{abs(offset) // 3600:02d}:{abs(offset) % 3600 // 60:02d}"
        ticks.append(GraphTick(elapsed, label, offset))
    paths = []
    last_row = None
    rows = list(DutyStatus)
    for interval in intervals:
        left = (interval.start_at - start).total_seconds() / duration
        right = (interval.end_at - start).total_seconds() / duration
        row = rows.index(interval.status)
        points = [] if last_row is None or last_row == row else [(left, last_row)]
        points += [(left, row), (right, row)]
        paths.append(GraphPath(interval.event_id, tuple(points)))
        last_row = row
    return LogGraph(tuple(ticks), tuple(paths))

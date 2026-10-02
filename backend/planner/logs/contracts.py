from dataclasses import dataclass
from datetime import datetime

from planner.contracts import DutyStatus


@dataclass(frozen=True)
class LogInterval:
    event_id: str | None
    status: DutyStatus
    start_at: datetime
    end_at: datetime
    distance_m: int
    assumed_outside_trip: bool


@dataclass(frozen=True)
class LogRemark:
    at: datetime
    location_label: str
    note: str
    event_id: str | None


@dataclass(frozen=True)
class GraphTick:
    elapsed_s: int
    label: str
    utc_offset_s: int


@dataclass(frozen=True)
class GraphPath:
    event_id: str | None
    points: tuple[tuple[float, int], ...]


@dataclass(frozen=True)
class LogGraph:
    ticks: tuple[GraphTick, ...]
    paths: tuple[GraphPath, ...]


@dataclass(frozen=True)
class DailyLog:
    date: str
    timezone: str
    start_at: datetime
    end_at: datetime
    duration_s: int
    intervals: tuple[LogInterval, ...]
    totals_s: dict[DutyStatus, int]
    distance_m: int
    remarks: tuple[LogRemark, ...]
    graph: LogGraph

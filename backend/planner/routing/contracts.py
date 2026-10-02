import time
from dataclasses import dataclass
from typing import Protocol

from planner.contracts import Location
from planner.errors import PlanningProblem

Coordinate = tuple[float, float]


@dataclass(frozen=True)
class RoadStep:
    instruction: str
    distance_m: int
    duration_s: int
    geometry: tuple[Coordinate, ...]


@dataclass(frozen=True)
class RoadLeg:
    id: str
    origin: Location
    destination: Location
    steps: tuple[RoadStep, ...]
    distance_m: int
    duration_s: int


@dataclass(frozen=True)
class StopPlace:
    id: str
    location: Location
    supports_fuel: bool
    supports_short_break: bool
    supports_long_rest: bool
    evidence: dict[str, str]


@dataclass(frozen=True)
class StopSearch:
    anchors: tuple[Coordinate, ...]
    radius_m: int
    needs_fuel: bool
    needs_long_rest: bool


@dataclass
class ProviderBudget:
    deadline_monotonic: float
    remaining_calls: int

    def check(self) -> float:
        remaining = self.deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise PlanningProblem("PLANNING_TIMEOUT", "Planning reached its time limit. Please try again.",
                                  504, True)
        if self.remaining_calls <= 0:
            raise PlanningProblem("SEARCH_BUDGET_EXHAUSTED", "The bounded stop search reached its call limit.")
        return remaining

    def consume(self, timeout: float) -> float:
        remaining = self.check()
        self.remaining_calls -= 1
        return min(timeout, remaining)


class RoutingProvider(Protocol):
    def search_locations(self, query: str, limit: int, budget: ProviderBudget) -> tuple[Location, ...]: ...
    def route(self, origin: Location, destination: Location, budget: ProviderBudget) -> RoadLeg: ...
    def matrix(self, origin: Location, destinations: tuple[Location, ...],
               budget: ProviderBudget) -> tuple[tuple[int, int] | None, ...]: ...


class StopProvider(Protocol):
    def find_candidates(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]: ...

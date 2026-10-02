from planner.routing.contracts import RoadLeg, StopPlace
from planner.routing.geometry import haversine_m


def projected_progress(leg: RoadLeg, place: StopPlace) -> int:
    """Geometry projection is only a ranking hint; actual road time decides feasibility."""
    closest = float("inf")
    progress = elapsed = 0
    for step in leg.steps:
        lengths = [haversine_m(a, b) for a, b in zip(step.geometry, step.geometry[1:])]
        total = sum(lengths)
        covered = 0
        for index, length in enumerate(lengths):
            a, b = step.geometry[index:index + 2]
            x, y = place.location.coordinate
            dx, dy = b[0] - a[0], b[1] - a[1]
            scale = dx * dx + dy * dy
            fraction = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / scale)) if scale else 0
            projected = a[0] + fraction * dx, a[1] + fraction * dy
            distance = haversine_m(projected, place.location.coordinate)
            if distance < closest:
                closest = distance
                progress = elapsed + round(step.duration_s * (covered + fraction * length) / total) if total else elapsed
            covered += length
        elapsed += step.duration_s
    return progress


def rank_candidates(candidates: tuple[StopPlace, ...], needs_fuel: bool, needs_long_rest: bool,
                    progress: dict[str, int], detour_seconds: dict[str, int]) -> tuple[StopPlace, ...]:
    eligible = (place for place in candidates if (not needs_fuel or place.supports_fuel)
                and (not needs_long_rest or place.supports_long_rest))
    return tuple(sorted(eligible, key=lambda place: (-progress.get(place.id, 0),
                                                     detour_seconds.get(place.id, 0), place.id)))

import math

from planner.routing.contracts import Coordinate, RoadLeg


def haversine_m(a: Coordinate, b: Coordinate) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    value = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1, math.sqrt(value)))


def distance_at_elapsed(leg: RoadLeg, elapsed_s: int) -> int:
    if elapsed_s <= 0:
        return 0
    if elapsed_s >= leg.duration_s:
        return leg.distance_m
    remaining = max(0, elapsed_s)
    distance = 0
    for step in leg.steps:
        if step.duration_s <= remaining:
            distance += step.distance_m
            remaining -= step.duration_s
        else:
            return distance + step.distance_m * remaining // step.duration_s
    return distance


def point_at_elapsed(leg: RoadLeg, elapsed_s: int) -> Coordinate:
    if elapsed_s <= 0:
        return leg.origin.coordinate
    if elapsed_s >= leg.duration_s:
        return leg.destination.coordinate
    remaining = max(0, elapsed_s)
    for step in leg.steps:
        if step.duration_s <= remaining:
            remaining -= step.duration_s
            continue
        fraction = remaining / step.duration_s
        distances = [haversine_m(a, b) for a, b in zip(step.geometry, step.geometry[1:])]
        offset = sum(distances) * fraction
        for index, distance in enumerate(distances):
            if offset <= distance and distance > 0:
                start, end = step.geometry[index:index + 2]
                ratio = offset / distance
                return start[0] + ratio * (end[0] - start[0]), start[1] + ratio * (end[1] - start[1])
            offset -= distance
        return step.geometry[-1]
    return leg.origin.coordinate


def boundary_elapsed(leg: RoadLeg, allowance_s: int, available_distance_m: int) -> int:
    """Last prospective point that fits time and fuel; road edges still require verification."""
    low, high = 0, min(leg.duration_s, max(0, allowance_s))
    while low < high:
        middle = (low + high + 1) // 2
        if distance_at_elapsed(leg, middle) <= available_distance_m:
            low = middle
        else:
            high = middle - 1
    return low

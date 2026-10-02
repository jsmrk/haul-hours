from planner.errors import PlanningProblem
from planner.routing.contracts import RoadLeg, RoadStep


class RoadNetworkFake:
    """Explicit directed road edges; unknown edges are unreachable, never straight-line fallbacks."""
    def __init__(self, edges=(), places=()):
        self.edges = {(edge.origin.id, edge.destination.id): edge for edge in edges}
        self.places = tuple(places)

    def route(self, origin, destination, budget):
        budget.check()
        if origin.coordinate == destination.coordinate:
            return RoadLeg(f"{origin.id}-{destination.id}", origin, destination, (), 0, 0)
        try:
            return self.edges[origin.id, destination.id]
        except KeyError:
            raise PlanningProblem("ROUTE_UNREACHABLE", "Fixture road edge is unreachable.", 422) from None

    def matrix(self, origin, destinations, budget):
        values = []
        for destination in destinations:
            try:
                edge = self.route(origin, destination, budget)
                values.append((edge.distance_m, edge.duration_s))
            except PlanningProblem:
                values.append(None)
        return tuple(values)

    def find_candidates(self, search, budget):
        budget.check()
        return tuple(place for place in self.places if
                     (not search.needs_fuel or place.supports_fuel)
                     and (not search.needs_long_rest or place.supports_long_rest))


def road(origin, destination, seconds, meters):
    return RoadLeg(f"{origin.id}-{destination.id}", origin, destination,
                   (RoadStep("Follow the test road", meters, seconds,
                             (origin.coordinate, destination.coordinate)),), meters, seconds)

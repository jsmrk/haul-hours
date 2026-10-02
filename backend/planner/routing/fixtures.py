"""Explicit development/test network. Geometry and travel times are illustrative.

Never used as a fallback for a failed live provider. Unknown directed edges are
unreachable, allowing browser tests to exercise the real bounded scheduler.
"""

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget, RoadLeg, RoadStep, StopPlace, StopSearch

FIXTURE_WARNING = "Test fixture data: routes, stops, and timing are illustrative; not live directions."


class FixtureNetwork:
    def __init__(self):
        places = [
            ("pittsburgh", "Pittsburgh, PA", -79.9959, 40.4406, "America/New_York"),
            ("harrisburg", "Harrisburg, PA", -76.8867, 40.2732, "America/New_York"),
            ("philadelphia", "Philadelphia, PA", -75.1652, 39.9526, "America/New_York"),
            ("san-diego", "San Diego, CA", -117.1611, 32.7157, "America/Los_Angeles"),
            ("los-angeles", "Los Angeles, CA", -118.2437, 34.0522, "America/Los_Angeles"),
            ("boston", "Boston, MA", -71.0589, 42.3601, "America/New_York"),
            ("miami", "Miami, FL", -80.1918, 25.7617, "America/New_York"),
            ("columbus", "Sample truck plaza — Columbus", -82.9988, 39.9612, "America/New_York"),
            ("st-louis", "Sample truck plaza — St. Louis", -90.1994, 38.6270, "America/Chicago"),
            ("albuquerque", "Sample truck plaza — Albuquerque", -106.6504, 35.0844, "America/Denver"),
            ("tucson", "Sample truck plaza — Tucson", -110.9747, 32.2226, "America/Phoenix"),
            ("flagstaff", "Sample fuel plaza — Flagstaff", -111.6513, 35.1983, "America/Phoenix"),
        ]
        self.locations = {row[0]: Location(*row) for row in places}
        rows = [
            ("pittsburgh", "harrisburg", 10800, 340000),
            ("harrisburg", "philadelphia", 7200, 170000),
            ("harrisburg", "san-diego", 120600, 3970000),
            ("harrisburg", "columbus", 27000, 720000),
            ("columbus", "san-diego", 93600, 3250000),
            ("columbus", "st-louis", 25200, 700000),
            ("st-louis", "san-diego", 68400, 2550000),
            ("st-louis", "albuquerque", 28800, 1250000),
            ("albuquerque", "san-diego", 39600, 1300000),
            ("albuquerque", "tucson", 25200, 800000),
            ("tucson", "san-diego", 14400, 500000),
            ("harrisburg", "los-angeles", 25200, 1900000),
            ("harrisburg", "flagstaff", 21600, 1250000),
            ("flagstaff", "los-angeles", 3600, 650000),
            ("harrisburg", "boston", 36000, 650000),
        ]
        self.edges = {(a, b): (seconds, meters) for a, b, seconds, meters in rows}
        self.stops = tuple(StopPlace(
            key, self.locations[key], True, True, key != "flagstaff",
            {"source": "illustrative test fixture", "amenity": "fuel", "hgv": "designated"},
        ) for key in ("columbus", "st-louis", "albuquerque", "tucson", "flagstaff"))

    def search_locations(self, query: str, limit: int, budget: ProviderBudget) -> tuple[Location, ...]:
        budget.check()
        return tuple(place for key, place in self.locations.items()
                     if not place.label.startswith("Sample") and query.casefold() in place.label.casefold())[:limit]

    def route(self, origin: Location, destination: Location, budget: ProviderBudget) -> RoadLeg:
        budget.check()
        if destination.id == "miami":
            raise PlanningProblem("PROVIDER_UNAVAILABLE", "Routing is temporarily unavailable. Please try again.", 503, True)
        if origin.coordinate == destination.coordinate:
            return RoadLeg(f"fixture-{origin.id}-{destination.id}", origin, destination, (), 0, 0)
        values = self.edges.get((origin.id, destination.id))
        if values is None:
            raise PlanningProblem("ROUTE_UNREACHABLE", "No route exists on this illustrative test network.", 422)
        seconds, meters = values
        step = RoadStep(f"Follow sample route to {destination.label}", meters, seconds,
                        (origin.coordinate, destination.coordinate))
        return RoadLeg(f"fixture-{origin.id}-{destination.id}", origin, destination, (step,), meters, seconds)

    def matrix(self, origin: Location, destinations: tuple[Location, ...], budget: ProviderBudget):
        budget.check()
        values = (self.edges.get((origin.id, destination.id)) for destination in destinations)
        return tuple((value[1], value[0]) if value else None for value in values)

    def find_candidates(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        budget.check()
        return tuple(stop for stop in self.stops if (not search.needs_fuel or stop.supports_fuel)
                     and (not search.needs_long_rest or stop.supports_long_rest))

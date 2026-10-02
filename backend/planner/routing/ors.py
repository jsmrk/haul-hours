import hashlib
import math
from functools import lru_cache

import httpx
from timezonefinder import TimezoneFinder

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.cache import TTLCache
from planner.routing.contracts import ProviderBudget, RoadLeg, RoadStep
from planner.routing.http import request_json


@lru_cache(maxsize=1)
def timezone_finder():
    return TimezoneFinder(in_memory=True)


def timezone_at(lon: float, lat: float) -> str:
    return timezone_finder().timezone_at(lng=lon, lat=lat) or "UTC"


def normalize_parts(values: list[float], total: int) -> list[int]:
    weight = sum(values)
    if weight <= 0:
        return [total] + [0] * (len(values) - 1)
    precise = [value / weight * total for value in values]
    result = [math.floor(value) for value in precise]
    order = sorted(range(len(values)), key=lambda i: (-(precise[i] - result[i]), i))
    for index in order[:total - sum(result)]:
        result[index] += 1
    return result


class ORSProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.openrouteservice.org",
                 client: httpx.Client | None = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client()
        self.cache = TTLCache()

    def _request(self, method: str, path: str, budget: ProviderBudget, **kwargs):
        if not self.api_key:
            raise PlanningProblem("PROVIDER_NOT_CONFIGURED", "Live routing needs an openrouteservice API key on the server.", 503)
        return request_json(self.client, method, self.base_url + path, budget,
                            headers={"Authorization": self.api_key, "User-Agent": "HaulHours/1.0"}, **kwargs)

    def search_locations(self, query: str, limit: int, budget: ProviderBudget) -> tuple[Location, ...]:
        key = ("geocode", query.lower().strip(), limit)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        data = self._request("GET", "/geocode/search", budget,
                             params={"text": query, "size": limit, "boundary.country": "US"})
        try:
            locations = []
            for feature in data["features"]:
                properties = feature["properties"]
                if properties.get("country_a") not in ("USA", "US"):
                    continue
                lon, lat = feature["geometry"]["coordinates"][:2]
                identifier = properties.get("gid") or properties["id"]
                locations.append(Location(str(identifier), properties["label"],
                                          float(lon), float(lat), timezone_at(lon, lat)))
            return self.cache.put(key, tuple(locations[:limit]), 7 * 86400)
        except (KeyError, TypeError, ValueError, IndexError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Address search returned invalid data.", 503, True) from None

    def route(self, origin: Location, destination: Location, budget: ProviderBudget) -> RoadLeg:
        leg_id = hashlib.sha256(repr((origin.coordinate, destination.coordinate)).encode()).hexdigest()[:16]
        if origin.coordinate == destination.coordinate:
            return RoadLeg(leg_id, origin, destination, (), 0, 0)
        key = ("route", origin, destination)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        data = self._request("POST", "/v2/directions/driving-hgv/geojson", budget, json={
            "coordinates": [origin.coordinate, destination.coordinate], "instructions": True,
            "options": {"avoid_features": ["ferries"], "avoid_borders": "all"},
        })
        try:
            feature = data["features"][0]
            geometry = tuple((float(p[0]), float(p[1])) for p in feature["geometry"]["coordinates"])
            properties = feature["properties"]
            distance = math.ceil(properties["summary"]["distance"])
            duration = math.ceil(properties["summary"]["duration"])
            if distance > 6_000_000:
                raise PlanningProblem("ROUTE_LIMIT_EXCEEDED", "A route leg exceeds the provider's 6,000 km limit.", 422)
            raw_steps = [step for segment in properties["segments"] for step in segment["steps"]]
            if not raw_steps or duration <= 0 or distance <= 0 or len(geometry) < 2:
                raise ValueError("Empty route")
            distances = normalize_parts([max(0, step["distance"]) for step in raw_steps], distance)
            durations = normalize_parts([max(0, step["duration"]) for step in raw_steps], duration)
            steps = []
            for index, raw in enumerate(raw_steps):
                start, end = raw["way_points"]
                points = geometry[start:end + 1]
                if not points:
                    raise ValueError("Missing geometry")
                steps.append(RoadStep(raw.get("instruction", "Continue"), distances[index], durations[index], points))
            leg = RoadLeg(leg_id, origin, destination, tuple(steps), distance, duration)
            return self.cache.put(key, leg, 86400)
        except (KeyError, TypeError, ValueError, IndexError, OverflowError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Truck directions returned invalid data.", 503, True) from None

    def matrix(self, origin: Location, destinations: tuple[Location, ...],
               budget: ProviderBudget) -> tuple[tuple[int, int] | None, ...]:
        if not destinations:
            return ()
        if len(destinations) > 5:
            raise ValueError("Matrix candidate limit is five")
        key = ("matrix", origin, destinations)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        data = self._request("POST", "/v2/matrix/driving-hgv", budget, json={
            "locations": [origin.coordinate, *(place.coordinate for place in destinations)],
            "sources": [0], "destinations": list(range(1, len(destinations) + 1)),
            "metrics": ["distance", "duration"], "units": "m",
        })
        try:
            distances, durations = data["distances"][0], data["durations"][0]
            if len(distances) != len(destinations) or len(durations) != len(destinations):
                raise ValueError("Invalid matrix length")
            result = tuple(None if d is None or t is None else (math.ceil(d), math.ceil(t))
                           for d, t in zip(distances, durations))
            return self.cache.put(key, result, 86400)
        except (KeyError, TypeError, ValueError, IndexError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Route estimates returned invalid data.", 503, True) from None

import httpx

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.cache import TTLCache
from planner.routing.contracts import ProviderBudget, StopPlace, StopSearch
from planner.routing.http import RequestPacer, request_json
from planner.routing.ors import timezone_at


class OverpassProvider:
    def __init__(self, url: str = "https://overpass-api.de/api/interpreter", client: httpx.Client | None = None, min_interval_s: float = 0):
        self.url = url
        self.client = client or httpx.Client()
        self.cache = TTLCache(128)
        self.pacer = RequestPacer(min_interval_s)

    def find_candidates(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        cached = self.cache.get(search)
        if cached is not None:
            return cached
        radius = min(2000, max(100, search.radius_m))
        fragments = []
        for lon, lat in search.anchors[:6]:
            circle = f"(around:{radius},{lat:.6f},{lon:.6f})"
            for tags in ('[amenity=fuel]', '[highway~"^(services|rest_area)$"]',
                         '[amenity=parking][hgv]', '[amenity=parking]["parking:hgv"]'):
                fragments.append(f"nwr{tags}{circle};")
        query = "[out:json][timeout:12];(" + "".join(fragments) + ");out center tags 100;"
        data = request_json(self.client, "POST", self.url, budget, 15, pacer=self.pacer, data={"data": query},
                            headers={"User-Agent": "HaulHours/1.0"})
        # Overpass can report query failures with HTTP 200 and partial/empty elements.
        # Such responses cannot prove that no stopping places exist and must not be cached.
        if data.get("remark"):
            raise PlanningProblem("PROVIDER_UNAVAILABLE", "Stop discovery is temporarily unavailable. Please try again.", 503, True)
        try:
            found = {}
            for element in data["elements"]:
                tags = element.get("tags", {})
                if any(tags.get(key) in ("no", "private") for key in ("access", "hgv", "motor_vehicle", "parking:hgv")):
                    continue
                point = element if "lon" in element else element.get("center", {})
                lon, lat = float(point["lon"]), float(point["lat"])
                fuel = tags.get("amenity") == "fuel" or tags.get("fuel") == "yes"
                parking = tags.get("parking:hgv") in ("yes", "designated") or tags.get("hgv") == "designated"
                parking = parking or (tags.get("amenity") == "parking" and tags.get("hgv") == "yes")
                service = tags.get("highway") in ("services", "rest_area")
                long_rest = parking or (service and tags.get("parking") in ("yes", "surface", "designated"))
                short_break = fuel or service or parking
                if search.needs_fuel and not fuel or search.needs_long_rest and not long_rest:
                    continue
                if not short_break:
                    continue
                identifier = f"osm:{element['type']}:{element['id']}"
                label = tags.get("name") or f"Mapped {'fuel stop' if fuel else 'rest area'} ({identifier})"
                place = StopPlace(identifier, Location(identifier, label, lon, lat, timezone_at(lon, lat)),
                                  fuel, short_break, long_rest, dict(tags))
                found[identifier] = place
            result = tuple(found[key] for key in sorted(found))[:100]
            return self.cache.put(search, result, 86400)
        except (KeyError, TypeError, ValueError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Stop discovery returned invalid map data.", 503, True) from None

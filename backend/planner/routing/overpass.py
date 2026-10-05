import logging
import math
from urllib.parse import urlsplit

import httpx

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.cache import TTLCache
from planner.routing.contracts import ProviderBudget, StopPlace, StopSearch
from planner.routing.http import RequestPacer, request_json
from planner.routing.ors import timezone_at

logger = logging.getLogger("haul_hours.providers")
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OverpassProvider:
    def __init__(self, url: str = DEFAULT_OVERPASS_URL, client: httpx.Client | None = None,
                 min_interval_s: float = 0, fallback_urls: tuple[str, ...] = ()):
        self.url = url
        self.urls = tuple(dict.fromkeys((url, *fallback_urls)))[:3]
        self.preferred_url = url
        self.client = client or httpx.Client()
        self.cache = TTLCache(128)
        self.area_cache = TTLCache(256)
        self.pacer = RequestPacer(min_interval_s)

    def find_candidates(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        cached = self.cache.get(search)
        if cached is not None:
            return cached
        found = {}
        for anchor in dict.fromkeys(search.anchors[:6]):
            window = StopSearch((anchor,), search.radius_m, search.needs_fuel, search.needs_long_rest)
            places = self.area_cache.get(window)
            if places is None:
                places = self._fetch_window(window, budget)
                self.area_cache.put(window, places, 86400)
            found.update((place.id, place) for place in places)
        return self.cache.put(search, tuple(found.values())[:100], 86400)

    def _fetch_window(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        query = self._query(search)
        urls = (self.preferred_url, *(url for url in self.urls if url != self.preferred_url))
        for url in urls:
            try:
                data = request_json(self.client, "POST", url, budget, 12, pacer=self.pacer, attempts=1,
                                    data={"data": query}, headers={"User-Agent": "HaulHours/1.0 (+https://github.com/jsmrk/haul-hours)"})
                places = self._places(data, search)
            except PlanningProblem as problem:
                if problem.code not in ("PROVIDER_UNAVAILABLE", "PROVIDER_INVALID_RESPONSE"):
                    raise
                logger.warning("stop_provider=%s code=%s", urlsplit(url).hostname, problem.code)
                continue
            self.preferred_url = url
            return places
        raise PlanningProblem("STOP_DISCOVERY_UNAVAILABLE",
                              "Could not look up fuel and rest stops because the stop data service is temporarily unavailable. Please try again.",
                              503, True)

    @staticmethod
    def _query(search: StopSearch) -> str:
        radius = min(2000, max(100, search.radius_m))
        if search.needs_fuel:
            filters = ('[amenity=fuel]', '[fuel=yes]')
        elif search.needs_long_rest:
            filters = ('["parking:hgv"]', '[amenity=parking][hgv~"^(yes|designated)$"]',
                       '[highway~"^(services|rest_area)$"][parking~"^(yes|surface|designated)$"]')
        else:
            filters = ('[amenity=fuel]', '[highway~"^(services|rest_area)$"]',
                       '[amenity=parking][hgv]', '["parking:hgv"]')
        boxes = []
        for lon, lat in dict.fromkeys(search.anchors[:6]):
            latitude_delta = radius / 111_320
            longitude_delta = latitude_delta / max(.1, math.cos(math.radians(lat)))
            box = f"({lat-latitude_delta:.6f},{lon-longitude_delta:.6f},{lat+latitude_delta:.6f},{lon+longitude_delta:.6f})"
            boxes.append(f"nwr{box};")
        # Materialize a small local set before testing tags. In particular, global
        # regex/tag intersections can time out even with a bbox on the statement.
        fragments = [f"nwr.near{tags};" for tags in filters]
        return "[out:json][timeout:10];(" + "".join(boxes) + ")->.near;(" + "".join(fragments) + ");out center tags 100;"

    @staticmethod
    def _places(data: dict, search: StopSearch) -> tuple[StopPlace, ...]:
        # Overpass can report query failures with HTTP 200 and partial/empty elements.
        # Such responses cannot prove that no stopping places exist and must not be cached.
        if data.get("remark"):
            raise PlanningProblem("PROVIDER_UNAVAILABLE", "Stop discovery is temporarily unavailable. Please try again.", 503, True)
        try:
            if not isinstance(data["elements"], list):
                raise ValueError("Invalid elements")
            found = {}
            for element in data["elements"]:
                if not isinstance(element, dict):
                    raise ValueError("Invalid element")
                tags = element.get("tags", {})
                if not isinstance(tags, dict):
                    raise ValueError("Invalid tags")
                if any(tags.get(key) in ("no", "private") for key in ("access", "hgv", "motor_vehicle", "parking:hgv")):
                    continue
                point = element if "lon" in element else element.get("center", {})
                lon, lat = float(point["lon"]), float(point["lat"])
                fuel = tags.get("amenity") == "fuel" or tags.get("fuel") == "yes"
                parking = tags.get("parking:hgv") in ("yes", "designated")
                parking = parking or (tags.get("amenity") == "parking" and tags.get("hgv") in ("yes", "designated"))
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
            return result
        except (KeyError, TypeError, ValueError, OverflowError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Stop discovery returned invalid map data.", 503, True) from None

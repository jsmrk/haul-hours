"""Real truck parking inventory and credentialed fuel search, without Overpass."""

import json
import math

import httpx

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.cache import TTLCache
from planner.routing.contracts import ProviderBudget, StopPlace, StopSearch
from planner.routing.http import RequestPacer, request_json
from planner.routing.ors import ORSProvider, timezone_at
from planner.routing.overpass import OverpassProvider

TRUCK_PARKING_URL = "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_Truck_Stop_Parking/FeatureServer/0"
USER_AGENT = "HaulHours/1.0 (+https://github.com/jsmrk/haul-hours)"


class LiveStopProvider:
    def __init__(self, routing: ORSProvider, parking_url: str = TRUCK_PARKING_URL,
                 client: httpx.Client | None = None):
        self.routing = routing
        self.parking_url = parking_url.rstrip("/")
        self.client = client or httpx.Client()
        self.cache = TTLCache(256)
        self.tags = TTLCache(512)
        self.pacer = RequestPacer(1)

    def find_candidates(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        cached = self.cache.get(search)
        if cached is not None:
            return cached
        if search.needs_fuel:
            places = self._fuel(search, budget)
        else:
            places = self._parking(search, budget)
            if not places and not search.needs_long_rest:
                places = self._fuel(search, budget)
        return self.cache.put(search, places, 86400)

    def _parking(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        data = request_json(self.client, "GET", self.parking_url + "/query", budget, pacer=self.pacer,
                            headers={"User-Agent": USER_AGENT}, params={
                                "f": "json", "where": "number_of_spots > 0", "outFields": "OBJECTID,nhs_rest_stop,number_of_spots",
                                "geometry": json.dumps({"points": search.anchors[:6], "spatialReference": {"wkid": 4326}}),
                                "geometryType": "esriGeometryMultipoint", "spatialRel": "esriSpatialRelIntersects",
                                "inSR": "4326", "outSR": "4326", "distance": "20000", "units": "esriSRUnit_Meter",
                                "resultRecordCount": "100", "returnGeometry": "true",
                            })
        try:
            if "error" in data or not isinstance(data["features"], list):
                raise ValueError("Invalid inventory")
            places = []
            for feature in data["features"][:100]:
                attributes = feature["attributes"]
                spaces = int(attributes["number_of_spots"] or 0)
                if spaces <= 0:
                    continue
                lon, lat = float(feature["geometry"]["x"]), float(feature["geometry"]["y"])
                if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
                    raise ValueError("Invalid coordinates")
                identifier = f"bts:{int(attributes['OBJECTID'])}"
                label = attributes["nhs_rest_stop"] or "DOT truck rest area"
                places.append(StopPlace(identifier, Location(identifier, label, lon, lat, timezone_at(lon, lat)),
                                        False, True, True, {"source": "USDOT/BTS NTAD Truck Stop Parking",
                                                          "inventory_date": "2019-04-09", "truck_spaces": str(spaces)}))
            return tuple(places)
        except (KeyError, TypeError, ValueError, OverflowError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "The truck-parking inventory returned invalid data. Please try again.", 503, True) from None

    def _fuel(self, search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]:
        path = "/openpoiservice/v0/pois" if httpx.URL(self.routing.base_url).host == "api.heigit.org" else "/pois"
        elements = {}
        for anchor in dict.fromkeys(search.anchors[:6]):
            key = ("fuel", anchor)
            features = self.cache.get(key)
            if features is None:
                data = self.routing._request("POST", path, budget, json={
                    "request": "pois", "geometry": {"geojson": {"type": "Point", "coordinates": anchor}, "buffer": 2000},
                    "filters": {"category_ids": [596]}, "limit": 10, "sortby": "distance",
                })
                if not isinstance(data.get("features"), list):
                    raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Fuel search returned invalid data.", 503, True)
                features = data["features"][:10]
            try:
                for feature in features:
                    properties = feature["properties"]
                    identifier = int(properties["osm_id"])
                    osm_type = {1: "node", 2: "way", 3: "relation"}[properties["osm_type"]]
                    lon, lat = map(float, feature["geometry"]["coordinates"][:2])
                    if identifier <= 0 or not math.isfinite(lon) or not math.isfinite(lat):
                        raise ValueError("Invalid POI")
                    record = self.tags.get((osm_type, identifier))
                    if record is None:
                        try:
                            data = request_json(self.client, "GET", f"https://api.openstreetmap.org/api/0.6/{osm_type}/{identifier}.json",
                                                budget, pacer=self.pacer, headers={"User-Agent": USER_AGENT})
                        except PlanningProblem as problem:
                            if problem.code == "ROUTE_UNREACHABLE":  # Deleted/outdated POI reference.
                                continue
                            raise
                        record = next(item for item in data["elements"] if item["id"] == identifier and item["type"] == osm_type)
                        # Validate evidence before retaining it; temporary malformed data
                        # must not poison the next attempt for the full cache lifetime.
                        OverpassProvider._places({"elements": [{**record, "lon": lon, "lat": lat}]}, search)
                        self.tags.put((osm_type, identifier), record, 86400)
                    elements[(osm_type, identifier)] = {**record, "lon": lon, "lat": lat}
                self.cache.put(key, features, 86400)
            except (KeyError, TypeError, ValueError, IndexError, StopIteration, OverflowError):
                raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "Fuel search returned invalid map evidence.", 503, True) from None
        return OverpassProvider._places({"elements": list(elements.values())}, search)

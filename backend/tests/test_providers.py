import json
import time

import httpx
import pytest

from planner.contracts import Location
from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget, RoadLeg, RoadStep, StopSearch
from planner.routing.geometry import distance_at_elapsed, point_at_elapsed
from planner.routing.ors import ORSProvider
from planner.routing.overpass import OverpassProvider

A = Location("a", "A", -80, 40, "America/New_York")
B = Location("b", "B", -79, 40, "America/New_York")


def budget():
    return ProviderBudget(time.monotonic() + 30, 20)


def test_step_profile_preserves_nonuniform_distance_and_coordinate_order():
    leg = RoadLeg("ab", A, B, (
        RoadStep("Slow road", 100, 100, ((-80, 40), (-79.5, 40))),
        RoadStep("Fast road", 900, 100, ((-79.5, 40), (-79, 40))),
    ), 1000, 200)
    assert distance_at_elapsed(leg, 100) == 100
    assert distance_at_elapsed(leg, 150) == 550
    assert distance_at_elapsed(leg, 200) == 1000
    assert point_at_elapsed(leg, 100) == (-79.5, 40)


@pytest.mark.parametrize("base_url,expected_url", [
    (None, "https://api.heigit.org/openrouteservice/v2/directions/driving-hgv/geojson"),
    ("https://api.heigit.org/", "https://api.heigit.org/openrouteservice/v2/directions/driving-hgv/geojson"),
    ("https://api.openrouteservice.org/", "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"),
    ("https://routing.example.test/ors/", "https://routing.example.test/ors/v2/directions/driving-hgv/geojson"),
])
def test_truck_route_uses_accepted_geojson_and_conserves_rounding(base_url, expected_url):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"features": [{"geometry": {"coordinates": [[-80, 40], [-79.5, 40], [-79, 40]]},
            "properties": {"summary": {"distance": 1000.1, "duration": 200.1}, "segments": [{"steps": [
                {"distance": 100.1, "duration": 100.1, "way_points": [0, 1], "instruction": "Turn right"},
                {"distance": 900, "duration": 100, "way_points": [1, 2], "instruction": "Continue"}]}]}}]})
    options = {} if base_url is None else {"base_url": base_url}
    provider = ORSProvider("secret", client=httpx.Client(transport=httpx.MockTransport(handler)), **options)
    leg = provider.route(A, B, budget())
    assert str(requests[0].url) == expected_url
    assert requests[0].method == "POST"
    assert requests[0].headers["Authorization"] == "secret"
    payload = json.loads(requests[0].content)
    assert payload["coordinates"] == [[-80, 40], [-79, 40]]
    assert payload["instructions"] is True
    assert payload["options"] == {"avoid_features": ["ferries"], "avoid_borders": "all"}
    assert sum(step.distance_m for step in leg.steps) == leg.distance_m == 1001
    assert sum(step.duration_s for step in leg.steps) == leg.duration_s == 201
    assert provider.route(A, B, budget()) == leg
    assert len(requests) == 1
    assert provider.route(A, A, budget()).duration_s == 0
    assert len(requests) == 1


@pytest.mark.parametrize("base_url,expected_url", [
    (None, "https://api.heigit.org/openrouteservice/v2/matrix/driving-hgv"),
    ("https://api.heigit.org/", "https://api.heigit.org/openrouteservice/v2/matrix/driving-hgv"),
    ("https://api.openrouteservice.org/", "https://api.openrouteservice.org/v2/matrix/driving-hgv"),
    ("https://routing.example.test/ors/", "https://routing.example.test/ors/v2/matrix/driving-hgv"),
])
def test_matrix_preserves_unreachable_entries(base_url, expected_url):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"distances": [[100, None]], "durations": [[10, None]]})
    options = {} if base_url is None else {"base_url": base_url}
    provider = ORSProvider("key", client=httpx.Client(transport=httpx.MockTransport(handler)), **options)
    assert provider.matrix(A, (B, A), budget()) == ((100, 10), None)
    assert str(requests[0].url) == expected_url
    assert requests[0].method == "POST"
    assert requests[0].headers["Authorization"] == "key"
    assert json.loads(requests[0].content) == {
        "locations": [[-80, 40], [-79, 40], [-80, 40]],
        "sources": [0], "destinations": [1, 2], "metrics": ["distance", "duration"], "units": "m",
    }
    assert provider.matrix(A, (B, A), budget()) == ((100, 10), None)
    assert len(requests) == 1


@pytest.mark.parametrize("base_url,expected_url", [
    (None, "https://api.heigit.org/pelias/v1/search"),
    ("https://api.heigit.org/", "https://api.heigit.org/pelias/v1/search"),
    ("https://api.openrouteservice.org/", "https://api.openrouteservice.org/geocode/search"),
    ("https://routing.example.test/ors/", "https://routing.example.test/ors/geocode/search"),
])
def test_geocoding_uses_us_filter_and_accepts_gid_without_an_id_field(base_url, expected_url):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"features": [
            {"geometry": {"coordinates": [-74, 40.7]}, "properties": {
                "gid": "pelias:ny", "label": "New York, NY", "country_a": "USA"}},
            {"geometry": {"coordinates": [-79, 43]}, "properties": {
                "gid": "pelias:ca", "label": "Canada", "country_a": "CAN"}},
        ]})
    options = {} if base_url is None else {"base_url": base_url}
    provider = ORSProvider("key", client=httpx.Client(transport=httpx.MockTransport(handler)), **options)
    locations = provider.search_locations("New York", 5, budget())
    assert str(requests[0].url.copy_with(query=None)) == expected_url
    assert requests[0].method == "GET"
    assert requests[0].headers["Authorization"] == "key"
    assert dict(requests[0].url.params) == {"text": "New York", "size": "5", "boundary.country": "US"}
    assert [location.id for location in locations] == ["pelias:ny"]
    assert locations[0].timezone == "America/New_York"
    assert provider.search_locations("New York", 5, budget()) == locations
    assert len(requests) == 1


@pytest.mark.parametrize("response,code,status", [
    (httpx.Response(429, headers={"Retry-After": "60"}), "PROVIDER_RATE_LIMITED", 429),
    (httpx.Response(200, text="broken"), "PROVIDER_INVALID_RESPONSE", 503),
    (httpx.Response(404, json={}), "ROUTE_UNREACHABLE", 422),
])
def test_provider_failures_are_explicit_and_do_not_expose_credentials(response, code, status):
    provider = ORSProvider("private-key", client=httpx.Client(transport=httpx.MockTransport(lambda req: response)))
    with pytest.raises(PlanningProblem) as caught:
        provider.route(A, B, budget())
    assert caught.value.code == code
    assert caught.value.status == status
    assert "private-key" not in caught.value.message


def test_timeouts_retry_once_and_budget_exhaustion_never_calls_transport():
    calls = []
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("upstream secret", request=request)
    provider = ORSProvider("secret", client=httpx.Client(transport=httpx.MockTransport(timeout)))
    with pytest.raises(PlanningProblem, match="unavailable"):
        provider.route(A, B, budget())
    assert len(calls) == 2
    with pytest.raises(PlanningProblem) as caught:
        provider.route(A, B, ProviderBudget(time.monotonic() - 1, 5))
    assert caught.value.status == 504
    assert len(calls) == 2


def test_stop_evidence_excludes_no_trucks_and_does_not_invent_overnight_parking():
    data = {"elements": [
        {"type": "node", "id": 1, "lon": -79, "lat": 40, "tags": {"amenity": "fuel", "name": "Fuel only"}},
        {"type": "node", "id": 2, "lon": -79, "lat": 40, "tags": {"amenity": "fuel", "hgv": "no"}},
        {"type": "way", "id": 3, "center": {"lon": -79, "lat": 40}, "tags": {"highway": "services", "parking:hgv": "yes", "name": "Truck plaza"}},
    ]}
    provider = OverpassProvider(client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=data))))
    places = provider.find_candidates(StopSearch(((-79, 40),), 2000, False, False), budget())
    assert [place.id for place in places] == ["osm:node:1", "osm:way:3"]
    assert places[0].supports_fuel and not places[0].supports_long_rest
    assert places[1].supports_long_rest


@pytest.mark.parametrize("elements", [[], [{"type": "node", "id": 1, "lon": -79, "lat": 40, "tags": {"amenity": "fuel"}}]])
def test_overpass_http_success_with_runtime_error_is_retryable_and_not_cached(elements):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"remark": "runtime error: Query timed out", "elements": elements})
    provider = OverpassProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))
    search = StopSearch(((-79, 40),), 2000, False, False)
    for _ in range(2):
        with pytest.raises(PlanningProblem) as caught:
            provider.find_candidates(search, budget())
        assert caught.value.status == 503 and caught.value.retryable
    assert len(calls) == 2


def test_cumulative_distance_includes_leading_instantaneous_steps_from_zero():
    provider = ORSProvider("key", client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"features": [{
            "geometry": {"coordinates": [[-80, 40], [-79.5, 40], [-79, 40]]},
            "properties": {"summary": {"distance": 1001, "duration": 101}, "segments": [{"steps": [
                {"distance": 1, "duration": .1, "way_points": [0, 1]},
                {"distance": 1000, "duration": 100.9, "way_points": [1, 2]},
            ]}]}}]}))))
    leg = provider.route(A, B, budget())
    assert leg.steps[0].duration_s == 0
    assert distance_at_elapsed(leg, 0) == 0
    assert distance_at_elapsed(leg, leg.duration_s) == leg.distance_m
    assert point_at_elapsed(leg, 0) == A.coordinate

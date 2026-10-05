import json
import time

import httpx
import pytest

from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget, StopSearch
from planner.routing.live_stops import LiveStopProvider
from planner.routing.ors import ORSProvider

SEARCH = StopSearch(((-79, 40), (-78, 40)), 2000, False, True)


def budget():
    return ProviderBudget(time.monotonic() + 30, 20)


def test_dot_truck_spaces_are_parking_evidence_but_never_fuel_evidence():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"features": [
            {"attributes": {"OBJECTID": 1, "nhs_rest_stop": "Mapped truck rest area", "number_of_spots": 24}, "geometry": {"x": -79, "y": 40}},
            {"attributes": {"OBJECTID": 2, "nhs_rest_stop": "No truck spaces", "number_of_spots": 0}, "geometry": {"x": -79, "y": 40}},
        ]})

    provider = LiveStopProvider(ORSProvider("private-key"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    places = provider.find_candidates(SEARCH, budget())
    assert len(places) == 1 and places[0].id == "bts:1"
    assert places[0].supports_long_rest and places[0].supports_short_break
    assert not places[0].supports_fuel
    assert places[0].evidence["truck_spaces"] == "24"
    assert requests[0].headers.get("Authorization") is None
    assert json.loads(requests[0].url.params["geometry"])["points"] == [[-79, 40], [-78, 40]]
    assert requests[0].url.params["outSR"] == "4326"
    assert provider.find_candidates(SEARCH, budget()) == places
    assert len(requests) == 1


@pytest.mark.parametrize("data", [{"error": {"message": "query failed"}}, {"features": {}}, {"features": [{"attributes": {}}]}])
def test_bad_parking_inventory_is_explicit_and_not_cached(data):
    provider = LiveStopProvider(ORSProvider("key"), client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=data))))
    for _ in range(2):
        with pytest.raises(PlanningProblem) as caught:
            provider.find_candidates(SEARCH, budget())
        assert caught.value.retryable and caught.value.code == "PROVIDER_INVALID_RESPONSE"


def test_live_fuel_lookup_verifies_osm_access_and_does_not_share_the_routing_key():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host == "api.heigit.org":
            assert request.headers["Authorization"] == "private-key"
            payload = json.loads(request.content)
            assert payload["filters"]["category_ids"] == [596]
            return httpx.Response(200, json={"features": [
                {"geometry": {"coordinates": [-79, 40]}, "properties": {"osm_id": identifier, "osm_type": 2}}
                for identifier in (1, 2)
            ]})
        assert request.headers.get("Authorization") is None
        identifier = int(request.url.path.rsplit("/", 1)[1].removesuffix(".json"))
        return httpx.Response(200, json={"elements": [{"id": identifier, "type": "way", "tags": {
            "amenity": "fuel", "name": "Mapped fuel", **({"hgv": "no"} if identifier == 2 else {})}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveStopProvider(ORSProvider("private-key", client=client), client=client)
    search = StopSearch(((-79, 40),), 2000, True, False)
    places = provider.find_candidates(search, budget())
    assert [place.id for place in places] == ["osm:way:1"]
    assert places[0].supports_fuel and not places[0].supports_long_rest
    assert provider.find_candidates(search, budget()) == places
    assert len(requests) == 3


def test_parking_inventory_empty_is_a_valid_result_not_an_outage():
    provider = LiveStopProvider(ORSProvider("key"), client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"features": []}))))
    assert provider.find_candidates(SEARCH, budget()) == ()


def test_malformed_poi_records_are_not_cached_and_can_recover():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(200, json={"features": [{}] if len(attempts) == 1 else []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveStopProvider(ORSProvider("key", client=client), client=client)
    search = StopSearch(((-79, 40),), 2000, True, False)
    with pytest.raises(PlanningProblem):
        provider.find_candidates(search, budget())
    assert provider.find_candidates(search, budget()) == ()
    assert len(attempts) == 2


@pytest.mark.parametrize("status", [404, 410])
def test_removed_osm_fuel_record_does_not_hide_other_valid_stations(status):
    records = []

    def handler(request):
        if request.url.host == "api.heigit.org":
            return httpx.Response(200, json={"features": [
                {"geometry": {"coordinates": [-79, 40]}, "properties": {"osm_id": identifier, "osm_type": 2}}
                for identifier in (1, 2)
            ]})
        identifier = int(request.url.path.rsplit("/", 1)[1].removesuffix(".json"))
        records.append(identifier)
        if identifier == 1:
            return httpx.Response(status)
        return httpx.Response(200, json={"elements": [{"id": 2, "type": "way", "tags": {
            "amenity": "fuel", "name": "Existing fuel station"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveStopProvider(ORSProvider("key", client=client), client=client)
    provider.pacer = type(provider.pacer)(0)
    places = provider.find_candidates(StopSearch(((-79, 40),), 2000, True, False), budget())
    assert [place.id for place in places] == ["osm:way:2"]
    assert records == [1, 2]

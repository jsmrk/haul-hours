import time

import httpx
import pytest

from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget, StopSearch
from planner.routing.overpass import OverpassProvider

PRIMARY = "https://primary.example.test/api/interpreter"
BACKUP = "https://backup.example.test/api/interpreter"
SEARCH = StopSearch(((-79, 40),), 2000, False, True)
TRUCK_STOP = {"elements": [{"type": "way", "id": 42, "center": {"lon": -79, "lat": 40},
                           "tags": {"amenity": "fuel", "parking:hgv": "yes", "name": "Mapped truck stop"}}]}


def budget(calls=20):
    return ProviderBudget(time.monotonic() + 30, calls)


@pytest.mark.parametrize("failure", ["timeout", "http", "runtime", "malformed", "invalid-elements", "invalid-record"])
def test_stop_discovery_fails_over_to_real_backup_data_and_caches_success(failure):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.host == "primary.example.test":
            if failure == "timeout":
                raise httpx.ReadTimeout("private upstream detail", request=request)
            if failure == "http":
                return httpx.Response(504)
            if failure == "runtime":
                return httpx.Response(200, json={"remark": "runtime error", **TRUCK_STOP})
            if failure == "invalid-elements":
                return httpx.Response(200, json={"elements": {}})
            if failure == "invalid-record":
                return httpx.Response(200, json={"elements": [None]})
            return httpx.Response(200, text="unreadable")
        return httpx.Response(200, json=TRUCK_STOP)

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)),
                                fallback_urls=(BACKUP,))
    allowance = budget()
    places = provider.find_candidates(SEARCH, allowance)
    assert [place.id for place in places] == ["osm:way:42"]
    assert places[0].supports_long_rest and places[0].supports_fuel
    assert calls == [PRIMARY, BACKUP]
    assert allowance.remaining_calls == 18
    assert provider.find_candidates(SEARCH, budget()) == places
    assert calls == [PRIMARY, BACKUP]
    provider.find_candidates(StopSearch(((-80, 40),), 2000, False, True), budget())
    assert calls[-1] == BACKUP and len(calls) == 3


def test_successful_empty_search_is_cached_without_failing_over():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"elements": []})

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)),
                                fallback_urls=(BACKUP,))
    assert provider.find_candidates(SEARCH, budget()) == ()
    assert provider.find_candidates(SEARCH, budget()) == ()
    assert calls == [PRIMARY]


def test_all_stop_endpoints_unavailable_returns_specific_retryable_error():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(503)

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)),
                                fallback_urls=(BACKUP, PRIMARY))
    for _ in range(2):
        with pytest.raises(PlanningProblem) as caught:
            provider.find_candidates(SEARCH, budget())
        assert caught.value.code == "STOP_DISCOVERY_UNAVAILABLE"
        assert caught.value.status == 503 and caught.value.retryable
        assert "fuel and rest stops" in caught.value.message.lower()
    assert calls == [PRIMARY, BACKUP, PRIMARY, BACKUP]


@pytest.mark.parametrize("status", [401, 403, 429])
def test_configuration_and_rate_limits_do_not_retry_or_rotate(status):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Retry-After": "30"})

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)),
                                fallback_urls=(BACKUP,))
    with pytest.raises(PlanningProblem) as caught:
        provider.find_candidates(SEARCH, budget())
    assert caught.value.status == (429 if status == 429 else 503)
    assert calls == [PRIMARY]


def test_stop_failover_never_exceeds_the_external_call_budget():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(504)

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)),
                                fallback_urls=(BACKUP,))
    with pytest.raises(PlanningProblem) as caught:
        provider.find_candidates(SEARCH, budget(calls=1))
    assert caught.value.code == "SEARCH_BUDGET_EXHAUSTED"
    assert calls == [PRIMARY]


def test_fuel_search_uses_small_bounding_boxes_and_avoids_unneeded_categories():
    queries = []

    def handler(request):
        from urllib.parse import parse_qs
        queries.append(parse_qs(request.content.decode())["data"][0])
        return httpx.Response(200, json=TRUCK_STOP)

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)))
    provider.find_candidates(StopSearch(((-79, 40), (-79, 40)), 2000, True, False), budget())
    assert "around:" not in queries[0]
    assert queries[0].count("[amenity=fuel]") == 1
    assert "[highway" not in queries[0]
    assert "->.near;" in queries[0]
    assert "nwr.near[amenity=fuel]" in queries[0]


def test_separate_search_windows_are_queried_once_and_reused_across_trips():
    queries = []

    def handler(request):
        queries.append(request.content)
        return httpx.Response(200, json=TRUCK_STOP)

    provider = OverpassProvider(PRIMARY, client=httpx.Client(transport=httpx.MockTransport(handler)))
    places = provider.find_candidates(StopSearch(((-79, 40), (-80, 40), (-79, 40)), 2000, False, True), budget())
    assert len(queries) == 2
    assert len(places) == 1
    provider.find_candidates(StopSearch(((-80, 40),), 2000, False, True), budget())
    assert len(queries) == 2

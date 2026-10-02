import time
from dataclasses import replace
from decimal import Decimal

import pytest

from planner.contracts import EventKind, Location
from planner.duty.audit import audit_timeline
from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget, StopPlace
from planner.scheduling.scheduler import schedule_trip
from planner.scheduling.summary import summarize_trip
from tests.network import RoadNetworkFake, road


def budget():
    return ProviderBudget(time.monotonic() + 30, 160)


def place(identifier, longitude, fuel=False, rest=False):
    return StopPlace(identifier, Location(identifier, identifier, longitude, 40, "America/New_York"),
                     fuel, True, rest, {"parking:hgv": "yes"} if rest else {"amenity": "fuel"})


def test_short_trip_counts_service_and_finishes_after_unloading(trip_request):
    a, b, c = trip_request.current_location, trip_request.pickup_location, trip_request.dropoff_location
    network = RoadNetworkFake((road(a, b, 3600, 100000), road(b, c, 3600, 100000)))
    trip = schedule_trip(trip_request, network, network, budget())
    summary = summarize_trip(trip)
    assert [event.kind for event in trip.events] == [EventKind.DRIVE, EventKind.PICKUP, EventKind.DRIVE, EventKind.DROPOFF]
    assert summary.driving_s == 7200 and summary.on_duty_s == 7200 and summary.elapsed_s == 14400
    assert (summary.completed_at - summary.dropoff_arrival_at).total_seconds() == 3600
    assert audit_timeline(trip_request, trip.events) == ()


def test_colocated_services_do_not_append_unnecessary_rest(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location,
                      dropoff_location=trip_request.current_location, cycle_used_hours=Decimal("70"))
    network = RoadNetworkFake()
    trip = schedule_trip(request, network, network, budget())
    assert [event.kind for event in trip.events] == [EventKind.PICKUP, EventKind.DROPOFF]
    assert summarize_trip(trip).elapsed_s == 7200
    assert summarize_trip(trip).distance_m == 0


@pytest.mark.parametrize("used", ["70", "69.50"])
@pytest.mark.parametrize("approach_seconds", [600, 3600])
def test_initial_restart_accounts_for_loading_before_more_driving(trip_request, used, approach_seconds):
    request = replace(trip_request, cycle_used_hours=Decimal(used))
    a, b, c = request.current_location, request.pickup_location, request.dropoff_location
    network = RoadNetworkFake((road(a, b, approach_seconds, 10000), road(b, c, 600, 10000)))
    trip = schedule_trip(request, network, network, budget())
    restarts = [event for event in trip.events if event.kind == EventKind.CYCLE_RESTART]
    assert len(restarts) == 1 and restarts[0].duration_s == 122400
    assert restarts[0].start_location == a
    assert audit_timeline(request, trip.events) == ()


def test_early_daily_rest_replaces_break_when_later_loading_leaves_no_exit_allowance(trip_request):
    a, b, c = trip_request.current_location, trip_request.pickup_location, trip_request.dropoff_location
    stop = place("rest", -79.3, rest=True)
    network = RoadNetworkFake((road(a, b, 39600, 700000), road(b, c, 3600, 50000),
                              road(a, stop.location, 27000, 450000), road(stop.location, b, 12600, 250000)), (stop,))
    trip = schedule_trip(trip_request, network, network, budget())
    assert any(event.kind == EventKind.DAILY_REST and event.poi_id == stop.id for event in trip.events)
    assert audit_timeline(trip_request, trip.events) == ()


def test_multi_day_route_chooses_parking_and_preserves_all_accepted_edges(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location)
    a, c = request.current_location, request.dropoff_location
    first, second = place("break", -79.4, rest=True), place("sleep", -79.1, rest=True)
    network = RoadNetworkFake((road(a, c, 54000, 1000000), road(a, first.location, 27000, 500000),
                              road(first.location, c, 27000, 500000), road(first.location, second.location, 10800, 200000),
                              road(second.location, c, 16200, 300000)), (first, second))
    trip = schedule_trip(request, network, network, budget())
    assert any(event.kind == EventKind.DAILY_REST for event in trip.events)
    assert any(event.kind == EventKind.BREAK for event in trip.events)
    assert summarize_trip(trip).distance_m == 1000000
    assert {leg.id for leg in trip.road_legs} == {"origin-break", "break-sleep", "sleep-dropoff"}
    assert audit_timeline(request, trip.events) == ()


def test_fuel_before_range_includes_detours_and_counts_fueling_as_break(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location)
    a, c = request.current_location, request.dropoff_location
    stop = place("truck-fuel", -79.2, fuel=True, rest=True)
    network = RoadNetworkFake((road(a, c, 27000, 1900000), road(a, stop.location, 20000, 1500000),
                              road(stop.location, c, 8000, 450000)), (stop,))
    trip = schedule_trip(request, network, network, budget())
    assert [event.kind for event in trip.events] == [EventKind.PICKUP, EventKind.DRIVE, EventKind.FUEL, EventKind.DRIVE, EventKind.DROPOFF]
    assert summarize_trip(trip).distance_m == 1950000
    assert audit_timeline(request, trip.events) == ()


def test_exact_fuel_range_arrival_does_not_require_post_trip_fuel(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location)
    network = RoadNetworkFake((road(request.current_location, request.dropoff_location, 7200, 1609344),))
    trip = schedule_trip(request, network, network, budget())
    assert summarize_trip(trip).fuel_stop_count == 0
    assert audit_timeline(request, trip.events) == ()


def test_fuel_only_dead_end_backtracks_to_stop_with_parking(trip_request):
    request = replace(trip_request, cycle_used_hours=Decimal("67"))
    a, c = request.pickup_location, request.dropoff_location
    bad = place("fuel-only", -78.7, fuel=True)
    good = place("truck-plaza", -79.1, fuel=True, rest=True)
    network = RoadNetworkFake((road(request.current_location, a, 60, 1000), road(a, c, 18000, 1900000),
                              road(a, bad.location, 7000, 1500000), road(bad.location, c, 7000, 450000),
                              road(a, good.location, 6000, 1200000), road(good.location, c, 12000, 700000)), (bad, good))
    trip = schedule_trip(request, network, network, budget())
    assert any(event.poi_id == good.id and event.kind == EventKind.CYCLE_RESTART for event in trip.events)
    assert not any(event.poi_id == bad.id for event in trip.events)
    assert audit_timeline(request, trip.events) == ()


def test_missing_stops_return_safe_prefix_without_fabricating_an_eta(trip_request):
    a, b, c = trip_request.current_location, trip_request.pickup_location, trip_request.dropoff_location
    network = RoadNetworkFake((road(a, b, 3600, 100000), road(b, c, 36000, 600000)))
    with pytest.raises(PlanningProblem) as caught:
        schedule_trip(trip_request, network, network, budget())
    assert caught.value.code == "NO_FEASIBLE_STOP_FOUND" and caught.value.status == 409
    assert [event.kind for event in caught.value.safe_prefix] == [EventKind.DRIVE, EventKind.PICKUP]
    assert audit_timeline(trip_request, caught.value.safe_prefix) == ()


def test_fuel_only_stop_can_leave_for_parking_before_later_cycle_exhaustion(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location, cycle_used_hours=Decimal("65"))
    a, c = request.current_location, request.dropoff_location
    fuel = place("fuel", -79.5, fuel=True)
    parking = place("parking", -79, rest=True)
    network = RoadNetworkFake((road(a, c, 18000, 3000000),
                              road(a, fuel.location, 6000, 1400000), road(fuel.location, c, 14000, 1600000),
                              road(fuel.location, parking.location, 3000, 400000), road(parking.location, c, 11000, 1200000)),
                             (fuel, parking))
    trip = schedule_trip(request, network, network, budget())
    assert any(event.kind == EventKind.FUEL and event.poi_id == fuel.id for event in trip.events)
    assert any(event.kind == EventKind.CYCLE_RESTART and event.poi_id == parking.id for event in trip.events)
    assert audit_timeline(request, trip.events) == ()


def test_matrix_estimate_cannot_authorize_an_overlong_actual_approach(trip_request):
    request = replace(trip_request, pickup_location=trip_request.current_location)
    a, c = request.current_location, request.dropoff_location
    bad, good = place("bad", -78.6, rest=True), place("good", -79.1, rest=True)
    class Underestimate(RoadNetworkFake):
        def matrix(self, origin, destinations, budget):
            return tuple((100000, 1000) for _ in destinations)
    network = Underestimate((road(a, c, 36000, 700000),
                             road(a, bad.location, 30000, 500000), road(bad.location, c, 6000, 200000),
                             road(a, good.location, 27000, 400000), road(good.location, c, 9000, 300000)), (bad, good))
    trip = schedule_trip(request, network, network, budget())
    assert not any(event.poi_id == bad.id for event in trip.events)
    assert any(event.poi_id == good.id for event in trip.events)
    assert audit_timeline(request, trip.events) == ()

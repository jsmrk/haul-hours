from datetime import datetime, timezone
from decimal import Decimal

from django.test import Client

from planner.contracts import DutyStatus, Location, LogMetadata, TripRequest, to_wire


def test_health_is_stateless():
    response = Client().get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "planner_version": "1"}


def test_decimal_and_aware_departure_survive_wire_serialization():
    location = Location("a", "New York, NY", -74.0, 40.7, "America/New_York")
    instant = datetime.fromisoformat("2026-10-02T08:00:00-04:00")
    request = TripRequest(location, location, location, Decimal("69.50"), instant,
                          "America/New_York", LogMetadata())
    payload = to_wire(request)
    assert payload["cycle_used_hours"] == "69.50"
    assert datetime.fromisoformat(payload["departure_at"]).astimezone(timezone.utc).hour == 12
    assert DutyStatus.D.value == "D"
    assert set(payload) >= {"current_location", "pickup_location", "dropoff_location", "cycle_used_hours"}

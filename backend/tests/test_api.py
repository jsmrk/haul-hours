import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client, override_settings

from planner.contracts import to_wire
from planner.errors import PlanningProblem
from planner.logs.days import build_daily_logs
from planner.logs.tokens import sign_log_bundle
from tests.network import RoadNetworkFake, road
from tests.test_logs import trip_at


def post(client, path, data):
    return client.post("/api/v1/" + path, data=json.dumps(data), content_type="application/json")


@pytest.mark.parametrize("used", ["0", "70", "69.50"])
def test_valid_plan_response_has_one_timeline_and_export_token(trip_request, used):
    request = replace(trip_request, cycle_used_hours=Decimal(used))
    a, b, c = request.current_location, request.pickup_location, request.dropoff_location
    network = RoadNetworkFake((road(a, b, 3600, 100000), road(b, c, 3600, 100000)))
    with patch("planner.api.views.get_providers", return_value=(network, network)):
        response = post(Client(), "trips/plan", to_wire(request))
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["driving_s"] == 7200
    assert data["summary"]["on_duty_s"] == 7200
    assert data["events"][-1]["kind"] == "dropoff"
    assert data["export_token"] and data["daily_logs"]
    from jsonschema import validate

    from planner.management.commands.export_schema import export_contract_schema
    schema = export_contract_schema()
    validate(data, {"$schema": schema["$schema"], "$ref": "#/definitions/PlanResult", "definitions": schema["definitions"]})


@pytest.mark.parametrize("used", ["-1", "70.01", "1.234", "NaN", "Infinity", "oops", 20])
def test_invalid_cycle_has_field_errors(trip_request, used):
    payload = to_wire(trip_request)
    payload["cycle_used_hours"] = used
    response = post(Client(), "trips/plan", payload)
    assert response.status_code == 400
    assert "cycle_used_hours" in response.json()["field_errors"]


@pytest.mark.parametrize("field,value", [("departure_at", "2026-10-02T12:00:00"),
                                         ("log_timezone", "Not/AZone")])
def test_naive_departure_and_invalid_zone_are_rejected(trip_request, field, value):
    payload = to_wire(trip_request)
    payload[field] = value
    response = post(Client(), "trips/plan", payload)
    assert response.status_code == 400 and field in response.json()["field_errors"]


def test_invalid_us_coordinates_and_mismatched_timezone_are_rejected(trip_request):
    payload = to_wire(trip_request)
    payload["current_location"]["latitude"] = 60
    response = post(Client(), "trips/plan", payload)
    assert response.status_code == 400
    assert "current_location" in response.json()["field_errors"]


@pytest.mark.parametrize("code,status", [("NO_FEASIBLE_STOP_FOUND", 409), ("ROUTE_LIMIT_EXCEEDED", 422),
                                       ("PROVIDER_RATE_LIMITED", 429), ("PROVIDER_UNAVAILABLE", 503),
                                       ("PLANNING_TIMEOUT", 504)])
def test_planning_problems_preserve_status_and_safe_prefix(trip_request, code, status):
    network = RoadNetworkFake()
    with patch("planner.api.views.get_providers", return_value=(network, network)), patch(
        "planner.api.views.schedule_trip", side_effect=PlanningProblem(code, "Useful explanation", status, status >= 429)):
        response = post(Client(), "trips/plan", to_wire(trip_request))
    assert response.status_code == status
    assert response.json()["code"] == code
    assert "summary" not in response.json()


def test_pdf_uses_signed_logs_without_providers_and_supports_single_day(trip_request):
    now = datetime.now(timezone.utc)
    logs = build_daily_logs(trip_at(trip_request, now, 7200))
    token = sign_log_bundle(logs)
    with patch("planner.api.views.get_providers", side_effect=AssertionError("No rerouting")):
        response = post(Client(), "logs/pdf", {"export_token": token, "metadata": {"driver_name": "Jess"}, "date": logs[0].date})
    assert response.status_code == 200 and response.content.startswith(b"%PDF")
    assert response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"]
    response = post(Client(), "logs/pdf", {"export_token": sign_log_bundle(logs, now - timedelta(days=2))})
    assert response.status_code == 410


@override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=100)
def test_large_payload_is_rejected_before_parsing():
    response = post(Client(), "trips/plan", {"large": "a" * 101})
    assert response.status_code == 413


def test_location_query_limits_and_provider_configuration():
    assert Client().get("/api/v1/locations?q=ab").status_code == 400
    with override_settings(ORS_API_KEY="", PROVIDER_MODE="live"):
        response = Client().get("/api/v1/locations?q=Boston&limit=5")
    assert response.status_code == 503


@pytest.mark.parametrize("departure", ["2026-10-03T03:00:00.123456Z", "2026-03-08T05:00:00.123456Z", "2026-11-01T04:00:00.123456Z"])
def test_fractional_departure_is_normalized_and_all_daily_seconds_are_conserved(trip_request, departure):
    payload = to_wire(trip_request)
    payload["departure_at"] = departure
    a, b, c = trip_request.current_location, trip_request.pickup_location, trip_request.dropoff_location
    network = RoadNetworkFake((road(a, b, 3600, 100001), road(b, c, 3600, 100001)))
    with patch("planner.api.views.get_providers", return_value=(network, network)):
        response = post(Client(), "trips/plan", payload)
    assert response.status_code == 200
    data = response.json()
    assert all(sum(log["totals_s"].values()) == log["duration_s"] for log in data["daily_logs"])
    assert sum(log["totals_s"]["D"] for log in data["daily_logs"]) == data["summary"]["driving_s"]
    assert datetime.fromisoformat(data["request"]["departure_at"]).microsecond == 0
    assert sum(log["distance_m"] for log in data["daily_logs"]) == data["summary"]["distance_m"]

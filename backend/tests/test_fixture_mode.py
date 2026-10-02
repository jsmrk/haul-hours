from django.test import Client, override_settings

from planner.api.views import get_providers
from planner.errors import PlanningProblem


@override_settings(DEBUG=True, PROVIDER_MODE="fixtures")
def test_explicit_fixture_mode_uses_real_scheduler_and_labels_results():
    response = Client().get("/api/v1/locations?q=Pittsburgh")
    assert response.status_code == 200
    assert response.json()["locations"][0]["label"] == "Pittsburgh, PA"
    assert Client().get("/api/v1/health")["X-Haul-Hours-Provider-Mode"] == "fixtures"


@override_settings(DEBUG=False, PROVIDER_MODE="fixtures")
def test_fixture_mode_refuses_production():
    try:
        get_providers()
    except PlanningProblem as problem:
        assert problem.code == "PROVIDER_CONFIGURATION_ERROR"
    else:
        raise AssertionError("Production must not silently serve fixture routes")

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache, wraps

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response

from planner.api.serializers import PDFExportRequestSerializer, TripRequestSerializer
from planner.constants import MAX_BODY_BYTES, MAX_PROVIDER_CALLS, PLANNER_VERSION, PLANNING_DEADLINE_S
from planner.contracts import LogMetadata, to_wire
from planner.errors import PlanningProblem
from planner.logs.days import build_daily_logs
from planner.logs.pdf import draw_log_pdf
from planner.logs.tokens import sign_log_bundle, verify_log_bundle
from planner.routing.contracts import ProviderBudget
from planner.routing.ors import ORSProvider
from planner.routing.overpass import OverpassProvider
from planner.scheduling.scheduler import schedule_trip
from planner.scheduling.summary import summarize_trip

logger = logging.getLogger("haul_hours.api")


@lru_cache(maxsize=4)
def provider_instances(key, base_url, overpass_url):
    return ORSProvider(key, base_url), OverpassProvider(overpass_url)


def get_providers():
    return provider_instances(settings.ORS_API_KEY, settings.ORS_BASE_URL, settings.OVERPASS_URL)


def flatten_errors(detail, prefix=""):
    if isinstance(detail, dict):
        return [message for key, value in detail.items() for message in flatten_errors(value, f"{prefix}{key}: ")]
    if isinstance(detail, list):
        return [message for value in detail for message in flatten_errors(value, prefix)]
    return [prefix + str(detail)]


def endpoint(view):
    @wraps(view)
    def handled(request, *args, **kwargs):
        request_id = uuid.uuid4().hex[:16]
        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
            if length > min(MAX_BODY_BYTES, settings.DATA_UPLOAD_MAX_MEMORY_SIZE):
                raise PlanningProblem("PAYLOAD_TOO_LARGE", "The request exceeds the 4 MB size limit.", 413)
            response = view(request, *args, **kwargs)
        except ValidationError as error:
            fields = {key: flatten_errors(value) for key, value in error.detail.items()} if isinstance(error.detail, dict) else {"__all__": flatten_errors(error.detail)}
            response = Response(PlanningProblem("INVALID_INPUT", "Please correct the highlighted fields.", 400,
                                                field_errors=fields).payload(), status=400)
        except (ParseError, ValueError):
            response = Response(PlanningProblem("INVALID_INPUT", "The request is not valid JSON or contains an invalid value.", 400).payload(), status=400)
        except RequestDataTooBig:
            response = Response(PlanningProblem("PAYLOAD_TOO_LARGE", "The request exceeds the size limit.", 413).payload(), status=413)
        except PlanningProblem as problem:
            logger.info("request=%s code=%s", request_id, problem.code)
            response = Response(problem.payload(), status=problem.status)
        response["X-Request-ID"] = request_id
        return response
    return handled


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "planner_version": PLANNER_VERSION})


@api_view(["GET"])
@endpoint
def locations(request):
    query = request.query_params.get("q", "").strip()
    try:
        limit = int(request.query_params.get("limit", "5"))
    except ValueError:
        limit = 0
    if not 3 <= len(query) <= 200 or not 1 <= limit <= 5:
        raise PlanningProblem("INVALID_INPUT", "Enter 3–200 characters and a result limit of 1–5.", 400,
                              field_errors={"q": ["Search a United States address or place."]})
    routing, _ = get_providers()
    budget = ProviderBudget(time.monotonic() + 25, 2)
    return Response({"locations": to_wire(routing.search_locations(query, limit, budget))})


@api_view(["POST"])
@endpoint
def plan(request):
    serializer = TripRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    domain = serializer.to_domain()
    routing, stops = get_providers()
    trip = schedule_trip(domain, routing, stops, ProviderBudget(time.monotonic() + PLANNING_DEADLINE_S, MAX_PROVIDER_CALLS))
    logs = build_daily_logs(trip)
    payload = {"request": to_wire(domain), "assumptions": [
        "Single property-carrying driver; 70 hours / 8 days; starts fully rested.",
        "One hour each for loading and unloading; 30 minutes on duty for fuel.",
        "Departure site permits waiting for an initial restart; fuel counter starts at zero.",
        "No adverse-condition, short-haul, split-sleeper, or appointment-window adjustments.",
        "Daily sheets use the selected home-terminal timezone; outside-trip time is assumed off duty.",
    ], "summary": to_wire(summarize_trip(trip)), "road_legs": to_wire(trip.road_legs),
        "events": to_wire(trip.events), "daily_logs": to_wire(logs), "warnings": list(trip.warnings),
        "planner_version": PLANNER_VERSION, "export_token": sign_log_bundle(logs)}
    if len(json.dumps(payload, separators=(",", ":")).encode()) > MAX_BODY_BYTES:
        raise PlanningProblem("RESULT_TOO_LARGE", "The route and logs exceed the 4 MB response size limit.", 413)
    return Response(payload)


@api_view(["POST"])
@endpoint
def export_pdf(request):
    serializer = PDFExportRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    logs = verify_log_bundle(data["export_token"], datetime.now(timezone.utc))
    if "date" in data:
        logs = tuple(log for log in logs if log.date == data["date"].isoformat())
        if not logs:
            raise PlanningProblem("INVALID_INPUT", "That date is not in this trip's logs.", 400)
    metadata = LogMetadata(**data["metadata"])
    pdf = draw_log_pdf(logs, metadata)
    filename = f"haul-hours-{logs[0].date}" + (f"-to-{logs[-1].date}" if len(logs) > 1 else "") + ".pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response

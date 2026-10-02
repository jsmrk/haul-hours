from rest_framework.decorators import api_view
from rest_framework.response import Response

from planner.constants import PLANNER_VERSION


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "planner_version": PLANNER_VERSION})

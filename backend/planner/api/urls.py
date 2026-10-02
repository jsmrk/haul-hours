from django.urls import path

from planner.api.views import health

urlpatterns = [path("health", health)]

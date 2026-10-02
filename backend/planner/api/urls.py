from django.urls import path

from planner.api.views import export_pdf, health, locations, plan

urlpatterns = [path("health", health), path("locations", locations), path("trips/plan", plan), path("logs/pdf", export_pdf)]

"""Health check URL patterns (no auth required)."""
from django.urls import path
from core.health import HealthzView, SystemStatusView

urlpatterns = [
    path("", HealthzView.as_view()),
    path("system-status", SystemStatusView.as_view()),
]

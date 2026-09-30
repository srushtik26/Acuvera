"""
Acuvera — Root URL configuration.
All app-level URLs are included here.
"""
from django.urls import path, include

urlpatterns = [
    # Health checks
    path("healthz", include("core.urls_health")),
    # Core auth + patients + encounters
    path("api/", include("core.urls")),
    # Triage engine
    path("api/", include("triage.urls")),
    # Allocation engine
    path("api/", include("allocation.urls")),
    # Escalation engine
    path("api/", include("escalation.urls")),
    # Admin analytics
    path("api/", include("analytics.urls")),
    # FHIR R4 adapter
    path("fhir/", include("fhir_adapter.urls")),
]

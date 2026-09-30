"""
Health check and system status endpoints.
GET /healthz           — liveness probe
GET /system-status     — system component health
"""
import logging
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.db import connection

logger = logging.getLogger("acuvera.health")


class HealthzView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


class SystemStatusView(View):
    def get(self, request):
        status = {"status": "ok", "components": {}}

        # DB health
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            status["components"]["db"] = "ok"
        except Exception as e:
            status["components"]["db"] = f"error: {e}"
            status["status"] = "degraded"

        # LLM availability
        flags = getattr(request, "feature_flags", settings.FEATURE_FLAGS_DEFAULT)
        if flags.get("LLM_ENABLED"):
            status["components"]["llm"] = "enabled"
        else:
            status["components"]["llm"] = "disabled"

        # APScheduler status
        try:
            from scheduler.jobs import get_scheduler_status
            status["components"]["scheduler"] = get_scheduler_status()
        except Exception:
            status["components"]["scheduler"] = "unknown"

        return JsonResponse(status)

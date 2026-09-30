"""
Analytics API views — admin dashboard, forecasting, financial impact.
GET /api/admin/overview/
GET /api/admin/doctor/{id}/utilization/
POST /api/admin/config/
GET /api/admin/forecast/?days=7
GET /api/admin/financial-impact/?period=monthly
"""
import logging
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAdmin, IsDeptHead, IsAuthenticatedViaJWT

logger = logging.getLogger("acuvera.analytics.views")


class AdminOverviewView(APIView):
    """GET /api/admin/overview/"""
    permission_classes = [IsDeptHead]

    def get(self, request):
        from analytics.engine import get_operational_overview
        dept_id = request.query_params.get("department")
        data = get_operational_overview(department_id=dept_id)
        return ok(data)


class DoctorUtilizationView(APIView):
    """GET /api/admin/doctor/{id}/utilization/"""
    permission_classes = [IsDeptHead]

    def get(self, request, doctor_id):
        from analytics.engine import get_doctor_utilization
        shift_hours = float(request.query_params.get("shift_hours", 8))
        data = get_doctor_utilization(str(doctor_id), shift_hours=shift_hours)
        if not data:
            return err("Doctor not found.", 404)
        return ok(data)


class AdminConfigView(APIView):
    """GET/POST /api/admin/config/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        from core.models import HospitalConfig
        from core.serializers import HospitalConfigSerializer
        config = HospitalConfig.objects.first()
        if not config:
            return ok({})
        return ok(HospitalConfigSerializer(config).data)

    def post(self, request):
        from core.models import HospitalConfig, Department
        from core.serializers import HospitalConfigSerializer

        config, _ = HospitalConfig.objects.get_or_create(
            hospital_name=request.data.get("hospital_name", "Acuvera Hospital")
        )
        serializer = HospitalConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return err(serializer.errors, 400)
        serializer.save()

        # Update department-level configs if provided
        dept_configs = request.data.get("department_configs", {})
        for dept_id, dept_cfg in dept_configs.items():
            try:
                dept = Department.objects.get(pk=dept_id)
                if "priority_weight_config" in dept_cfg:
                    dept.priority_weight_config = dept_cfg["priority_weight_config"]
                if "starvation_threshold_minutes" in dept_cfg:
                    dept.starvation_threshold_minutes = dept_cfg["starvation_threshold_minutes"]
                dept.save()
            except Department.DoesNotExist:
                pass

        from core.audit import log_audit
        log_audit("admin.config_update", "hospital_config", config.id, request.acuvera_user,
                  None, None, request)
        return ok(serializer.data)


class ForecastView(APIView):
    """GET /api/admin/forecast/?days=7&department=<id>"""
    permission_classes = [IsDeptHead]

    def get(self, request):
        from analytics.engine import compute_peak_hour_forecast, compute_staffing_suggestion
        dept_id = request.query_params.get("department")
        days = int(request.query_params.get("days", 7))

        if not dept_id:
            from core.models import Department
            first_dept = Department.objects.filter(is_active=True).first()
            if not first_dept:
                return err("No active departments found.", 404)
            dept_id = str(first_dept.id)

        forecast = compute_peak_hour_forecast(dept_id, days_ahead=days)

        # Staffing suggestion at peak
        peak = forecast["hourly_forecast"].get(forecast["peak_hour"], {})
        peak_expected = peak.get("expected", 1)
        staffing = compute_staffing_suggestion(
            expected_arrivals_per_hour=peak_expected,
            avg_handling_minutes=30,
            target_avg_wait_minutes=15,
        )

        return ok({**forecast, "staffing_suggestion": staffing})


class FinancialImpactView(APIView):
    """GET /api/admin/financial-impact/?period=monthly&department=<id>"""
    permission_classes = [IsDeptHead]

    def get(self, request):
        from analytics.engine import compute_financial_impact
        dept_id = request.query_params.get("department")
        period = request.query_params.get("period", "monthly")
        period_days = {"weekly": 7, "monthly": 30, "quarterly": 90}.get(period, 30)

        if not dept_id:
            from core.models import Department
            first_dept = Department.objects.filter(is_active=True).first()
            if not first_dept:
                return err("No active departments found.", 404)
            dept_id = str(first_dept.id)

        data = compute_financial_impact(dept_id, period_days=period_days)
        return ok(data)


class StarvationAlertsView(APIView):
    """GET /api/admin/starvation-alerts/ — real-time starving encounters list."""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        from core.models import Encounter
        from core.serializers import EncounterSerializer
        from django.utils import timezone

        dept_id = request.query_params.get("department")
        now = timezone.now()

        qs = Encounter.objects.filter(
            status__in=("waiting", "assigned"),
            is_deleted=False,
        ).select_related("department", "patient", "assigned_doctor")

        if dept_id:
            qs = qs.filter(department_id=dept_id)

        starving = []
        for enc in qs:
            threshold_min = enc.department.starvation_threshold_minutes
            wait_min = (now - enc.created_at).total_seconds() / 60.0
            if wait_min > threshold_min:
                data = EncounterSerializer(enc).data
                data["wait_minutes"] = round(wait_min, 1)
                data["threshold_minutes"] = threshold_min
                starving.append(data)

        return ok(starving)


class AnalyticsSnapshotHistoryView(APIView):
    """GET /api/admin/snapshots/?department=<id>&days=30"""
    permission_classes = [IsDeptHead]

    def get(self, request):
        from core.models import AnalyticsSnapshot
        from datetime import timedelta
        from django.utils import timezone

        dept_id = request.query_params.get("department")
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now().date() - timedelta(days=days)

        qs = AnalyticsSnapshot.objects.filter(date__gte=cutoff).order_by("-date")
        if dept_id:
            qs = qs.filter(department_id=dept_id)

        data = list(qs.values(
            "id", "date", "department_id", "avg_wait_time", "starvation_count",
            "escalation_count", "throughput", "doctor_utilization_json",
        ))
        return ok(data)

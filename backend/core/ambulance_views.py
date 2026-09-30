"""
Ambulance Pre-Triage system.
POST /api/encounters/ambulance/   — Paramedic pre-registers incoming patient
GET  /api/encounters/incoming/    — Nurse fetches all incoming ambulances

Secured with X-Ambulance-Key: <AMBULANCE_TOKEN> header.
"""
import logging
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.models import Patient, Encounter, Department
from core.serializers import EncounterSerializer

logger = logging.getLogger("acuvera.ambulance")

AMBULANCE_TOKEN = getattr(settings, "AMBULANCE_TOKEN", "acuvera-demo-ambulance")


def _check_ambulance_auth(request):
    key = request.headers.get("X-Ambulance-Key", "")
    return key == AMBULANCE_TOKEN


class AmbulancePreRegisterView(APIView):
    """POST /api/encounters/ambulance/ — Paramedic submits patient en-route."""
    permission_classes = []  # Custom token auth below

    def post(self, request):
        if not _check_ambulance_auth(request):
            return err(
                "Ambulance authentication required. Pass X-Ambulance-Key header.",
                401
            )

        data = request.data
        eta_minutes = int(data.get("eta_minutes", 5))
        if eta_minutes < 1 or eta_minutes > 120:
            return err("eta_minutes must be between 1 and 120.", 400)

        dept = Department.objects.filter(is_active=True).first()
        if not dept:
            return err("No active department configured.", 500)

        # Create patient — name optional (may be unknown in emergency)
        patient = Patient.objects.create(
            name=data.get("patient_name") or "Unknown (Ambulance)",
            age=data.get("age"),
            gender=data.get("gender", "unknown"),
        )

        # Create encounter in 'incoming' status
        enc = Encounter.objects.create(
            patient=patient,
            department=dept,
            status="incoming",
            eta_minutes=eta_minutes,
            eta_set_at=timezone.now(),
            notes=data.get("chief_complaint", "Ambulance pre-registration"),
            triage_stage="rapid",
        )

        # Run preliminary triage if vitals provided
        vitals = data.get("vitals", {})
        symptoms = data.get("symptoms", [])
        if vitals or symptoms:
            try:
                from triage.engine import compute_triage
                compute_triage(
                    encounter_id=str(enc.id),
                    vitals=vitals,
                    symptoms=symptoms,
                    red_flags=data.get("red_flags", {}),
                    patient_age=patient.age,
                )
                logger.info("Pre-triage complete for ambulance encounter %s", enc.id)
            except Exception as e:
                logger.warning("Ambulance pre-triage failed: %s", e)

        logger.info(
            "Ambulance pre-registration: encounter=%s eta=%dmin patient=%s",
            enc.id, eta_minutes, patient.name
        )

        return ok({
            "encounter_id": str(enc.id),
            "patient_name": patient.name,
            "eta_minutes": eta_minutes,
            "eta_set_at": enc.eta_set_at.isoformat(),
            "department": dept.name,
            "message": f"Patient pre-registered. Preparing bay. ETA: {eta_minutes} minutes.",
        }, status=201)


class IncomingAmbulanceListView(APIView):
    """GET /api/encounters/incoming/ — Nurse sees all incoming ambulances with ETA countdown."""
    permission_classes = []  # Accessible to authenticated users — use IsAuthenticatedViaJWT if needed

    def get(self, request):
        from core.permissions import IsAuthenticatedViaJWT
        # Lightweight auth check
        perm = IsAuthenticatedViaJWT()
        if not perm.has_permission(request, self):
            return err("Authentication required.", 401)

        now = timezone.now()
        incoming = Encounter.objects.filter(
            status="incoming", is_deleted=False
        ).select_related("patient", "department", "triage_data").order_by("eta_set_at")

        results = []
        for enc in incoming:
            if enc.eta_set_at and enc.eta_minutes:
                elapsed_seconds = (now - enc.eta_set_at).total_seconds()
                remaining_seconds = max(0, int(enc.eta_minutes * 60 - elapsed_seconds))
            else:
                remaining_seconds = 0

            vitals = {}
            symptoms = []
            try:
                vitals = enc.triage_data.vitals_json or {}
                symptoms = enc.triage_data.symptoms_json or []
            except Exception:
                pass

            results.append({
                "encounter_id": str(enc.id),
                "patient_name": enc.patient.name,
                "age": enc.patient.age,
                "gender": enc.patient.gender,
                "chief_complaint": enc.notes,
                "priority": enc.priority,
                "risk_score": enc.risk_score,
                "eta_minutes": enc.eta_minutes,
                "remaining_seconds": remaining_seconds,
                "eta_set_at": enc.eta_set_at.isoformat() if enc.eta_set_at else None,
                "vitals": vitals,
                "symptoms": symptoms,
                "department": enc.department.name if enc.department else None,
            })

        return ok(results)

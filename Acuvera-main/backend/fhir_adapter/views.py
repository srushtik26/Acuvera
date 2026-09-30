"""
FHIR R4 API views — HTTP endpoints for EHR integration.
Basic auth (configurable via env vars).
"""
import base64
import json
import logging
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger("acuvera.fhir.views")


def fhir_auth(request) -> bool:
    """Validate HTTP Basic Auth for FHIR endpoints."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username == settings.FHIR_BASIC_USERNAME and password == settings.FHIR_BASIC_PASSWORD
    except Exception:
        return False


def fhir_response(resource, status=200):
    return JsonResponse(resource, status=status, content_type="application/fhir+json")


def fhir_error(msg, status=400, code="invalid"):
    return fhir_response({
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": code, "diagnostics": msg}]
    }, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class FHIRPatientView(View):
    """POST /fhir/Patient — create or retrieve patient."""

    def post(self, request):
        if not fhir_auth(request):
            return fhir_error("Unauthorized", 401, "security")
        try:
            resource = json.loads(request.body)
        except json.JSONDecodeError:
            return fhir_error("Invalid JSON body", 400)
        if resource.get("resourceType") != "Patient":
            return fhir_error("Expected resourceType Patient", 422)

        from fhir_adapter.adapter import fhir_patient_to_internal, internal_patient_to_fhir
        from core.models import Patient

        patient_data = fhir_patient_to_internal(resource)
        patient = Patient.objects.create(**{k: v for k, v in patient_data.items() if v is not None})
        return fhir_response(internal_patient_to_fhir(patient), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class FHIREncounterView(View):
    """POST /fhir/Encounter"""

    def post(self, request):
        if not fhir_auth(request):
            return fhir_error("Unauthorized", 401, "security")
        try:
            resource = json.loads(request.body)
        except json.JSONDecodeError:
            return fhir_error("Invalid JSON body", 400)

        from fhir_adapter.adapter import fhir_encounter_to_internal, internal_encounter_to_fhir
        from core.models import Patient, Department, Encounter

        data = fhir_encounter_to_internal(resource)
        try:
            patient = Patient.objects.get(pk=data["patient_id"])
            dept = Department.objects.get(pk=data["department_id"])
        except (Patient.DoesNotExist, Department.DoesNotExist) as e:
            return fhir_error(f"Reference not found: {e}", 422)

        encounter = Encounter.objects.create(
            patient=patient, department=dept,
            status=data.get("status", "waiting"),
            triage_stage=data.get("triage_stage", "rapid"),
            priority="moderate",
        )
        return fhir_response(internal_encounter_to_fhir(encounter), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class FHIRObservationView(View):
    """POST /fhir/Observation — add vitals to encounter triage data."""

    def post(self, request):
        if not fhir_auth(request):
            return fhir_error("Unauthorized", 401, "security")
        try:
            resource = json.loads(request.body)
        except json.JSONDecodeError:
            return fhir_error("Invalid JSON body", 400)

        from fhir_adapter.adapter import fhir_observation_to_triagedata
        from core.models import Encounter, TriageData

        data = fhir_observation_to_triagedata(resource)
        if not data.get("encounter_id"):
            return fhir_error("Observation must reference an Encounter", 422)

        try:
            enc = Encounter.objects.get(pk=data["encounter_id"])
        except Encounter.DoesNotExist:
            return fhir_error("Encounter not found", 404)

        td, _ = TriageData.objects.get_or_create(encounter=enc)
        vitals = dict(td.vitals_json or {})
        vitals.update(data.get("vitals", {}))
        td.vitals_json = vitals
        td.save()

        return fhir_response({"resourceType": "Observation", "id": str(td.id), "status": "final"}, 201)


@method_decorator(csrf_exempt, name="dispatch")
class FHIRTaskView(View):
    """POST /fhir/Task — create doctor assignment task."""

    def post(self, request):
        if not fhir_auth(request):
            return fhir_error("Unauthorized", 401, "security")
        try:
            resource = json.loads(request.body)
        except json.JSONDecodeError:
            return fhir_error("Invalid JSON body", 400)

        encounter_ref = resource.get("focus", {}).get("reference", "")
        owner_ref = resource.get("owner", {}).get("reference", "")
        encounter_id = encounter_ref.split("/")[-1] if "/" in encounter_ref else None
        doctor_id = owner_ref.split("/")[-1] if "/" in owner_ref else None

        if not encounter_id or not doctor_id:
            return fhir_error("Task must have focus (Encounter) and owner (Practitioner)", 422)

        from allocation.engine import try_assign_doctor
        from core.models import Encounter
        success = try_assign_doctor(encounter_id, doctor_id, reason="fhir_task")
        if not success:
            return fhir_error("Assignment failed", 409)

        enc = Encounter.objects.get(pk=encounter_id)
        return fhir_response({
            "resourceType": "Task",
            "status": "completed",
            "focus": {"reference": f"Encounter/{encounter_id}"},
            "owner": {"reference": f"Practitioner/{doctor_id}"},
        }, 201)

"""
Assessment API views.
POST   /api/encounters/{id}/assessment/          — start or save assessment (doctor only)
GET    /api/encounters/{id}/assessment/          — get assessment (any authenticated)
POST   /api/encounters/{id}/assessment/complete/ — complete + generate LLM report
"""
import logging
from django.utils import timezone
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAuthenticatedViaJWT, IsDoctor
from core.models import Encounter, Assessment
from core.serializers import AssessmentSerializer
from core.audit import log_audit

logger = logging.getLogger("acuvera.assessment")


class AssessmentView(APIView):
    """GET/POST /api/encounters/{pk}/assessment/"""

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticatedViaJWT()]
        return [IsDoctor()]

    def get(self, request, pk):
        """Return the assessment for an encounter (for nurse report view, etc.)."""
        try:
            enc = Encounter.objects.get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        try:
            assessment = enc.assessment
        except Assessment.DoesNotExist:
            return ok(None)

        return ok(AssessmentSerializer(assessment).data)

    def post(self, request, pk):
        """Start or update an assessment session. Creates if not exists."""
        try:
            enc = Encounter.objects.get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        if enc.assigned_doctor_id and str(enc.assigned_doctor_id) != str(request.acuvera_user.id):
            return err("You can only assess cases assigned to you.", 403)

        # Create or update
        assessment, created = Assessment.objects.get_or_create(
            encounter=enc,
            defaults={"doctor": request.acuvera_user},
        )

        if assessment.completed_at:
            return err("Assessment already completed.", 409)

        # Update doctor if case was referred/reassigned
        if not created and str(assessment.doctor_id) != str(request.acuvera_user.id):
            assessment.doctor = request.acuvera_user

        # Update fields
        notes = request.data.get("notes")
        if notes is not None:
            assessment.notes = notes

        # Merge new media into existing list
        new_media = request.data.get("media")  # list of {name, mime_type, data_b64}
        if new_media and isinstance(new_media, list):
            existing = assessment.media_json or []
            existing.extend(new_media)
            assessment.media_json = existing

        assessment.save()

        if created:
            # Mark encounter as in_progress when assessment starts
            if enc.status == "assigned":
                enc.status = "in_progress"
                enc.version += 1
                enc.save()

        log_audit(
            "assessment.update", "encounter", enc.id,
            request.acuvera_user, None, None, request,
            metadata={"created": created, "notes_length": len(assessment.notes)},
        )

        return ok(AssessmentSerializer(assessment).data, status=201 if created else 200)


class CompleteAssessmentView(APIView):
    """POST /api/encounters/{pk}/assessment/complete/ — finalize + generate report."""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            enc = Encounter.objects.select_related(
                "patient", "department", "assigned_doctor"
            ).get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        if enc.assigned_doctor_id and str(enc.assigned_doctor_id) != str(request.acuvera_user.id):
            return err("Only the assigned doctor can complete this assessment.", 403)

        # Create if not exists (e.g. if previous doctor never saved notes)
        assessment, created = Assessment.objects.get_or_create(
            encounter=enc,
            defaults={"doctor": request.acuvera_user},
        )

        if assessment.completed_at:
            return err("Assessment already completed.", 409)

        # Take over doctor field if case was referred
        if not created and str(assessment.doctor_id) != str(request.acuvera_user.id):
            assessment.doctor = request.acuvera_user

        # Final notes save
        final_notes = request.data.get("notes", assessment.notes)
        assessment.notes = final_notes

        # Generate LLM report
        report_text = self._generate_report(enc, assessment, request.feature_flags)
        assessment.report_text = report_text
        assessment.completed_at = timezone.now()
        assessment.save()

        # Mark encounter as completed
        enc.status = "completed"
        enc.version += 1
        enc.save()

        log_audit(
            "assessment.complete", "encounter", enc.id,
            request.acuvera_user, None, None, request,
            metadata={"report_generated": bool(report_text)},
        )

        logger.info("Assessment completed for encounter %s", pk)
        return ok(AssessmentSerializer(assessment).data)

    def _generate_report(self, enc, assessment, feature_flags) -> str:
        """Generate a clinical visit summary via GROQ, with deterministic fallback."""
        vitals = {}
        symptoms = []
        chief_complaint = ""

        try:
            td = enc.triage_data
            vitals = td.vitals_json or {}
            symptoms = td.symptoms_json or []
            chief_complaint = td.raw_input_text or ""
        except Exception:
            pass

        # Build deterministic base report
        vitals_str = ", ".join(f"{k}: {v}" for k, v in vitals.items() if v is not None) or "Not recorded"
        symptoms_str = ", ".join(symptoms) or "Not recorded"
        doc_notes = assessment.notes or "No doctor notes recorded."
        patient = enc.patient
        age = patient.age or "?"
        gender = patient.gender or "unknown"

        base = (
            f"EMERGENCY DEPARTMENT VISIT SUMMARY\n"
            f"{'=' * 48}\n"
            f"Priority: {enc.priority.upper()}  |  Risk Score: {enc.risk_score}  |  Confidence: {enc.confidence_score}%\n"
            f"Chief Complaint: {chief_complaint or 'Not recorded'}\n\n"
            f"VITALS AT PRESENTATION\n"
            f"{'-' * 30}\n"
            f"{vitals_str or 'Not recorded'}\n\n"
            f"PRESENTING SYMPTOMS\n"
            f"{'-' * 30}\n"
            f"{symptoms_str or 'Not recorded'}"
        )

        # Try LLM
        if feature_flags.get("LLM_ENABLED"):
            try:
                from llm_sidecar.client import call_groq
                from llm_sidecar.prompts import VISIT_SUMMARY_PROMPT
                # age_group safe proxy
                age_group = "unknown"
                if patient.age:
                    if patient.age < 18: age_group = "pediatric"
                    elif patient.age < 40: age_group = "young adult"
                    elif patient.age < 60: age_group = "middle-aged adult"
                    else: age_group = "senior adult"

                prompt = VISIT_SUMMARY_PROMPT.format(
                    age_group=age_group,
                    chief_complaint=chief_complaint or "Not stated",
                    vitals=vitals_str,
                    symptoms=symptoms_str,
                    priority=enc.priority.upper(),
                    score=enc.risk_score,
                    doctor_notes=doc_notes,
                )
                llm_text = call_groq(
                    "You produce concise, accurate clinical visit summaries. No PHI. Plain text only.",
                    prompt,
                    feature_flags,
                    max_tokens=200,
                )
                if llm_text:
                    return llm_text.strip()
            except Exception as e:
                logger.warning("LLM report generation failed: %s", e)

        return base

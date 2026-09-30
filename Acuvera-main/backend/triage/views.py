"""
Triage API views.
POST /api/triage/{encounter_id}/analyze/ — run triage engine.
"""
import logging
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.models import Encounter, TriageData
from core.permissions import IsAuthenticatedViaJWT
from core.serializers import AnalyzeTriageSerializer, EncounterSerializer
from core.audit import log_audit

logger = logging.getLogger("acuvera.triage.views")


class AnalyzeTriageView(APIView):
    """POST /api/triage/{encounter_id}/analyze/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request, encounter_id):
        # Validate input
        serializer = AnalyzeTriageSerializer(data=request.data)
        if not serializer.is_valid():
            return err(serializer.errors, 400)
        data = serializer.validated_data

        # Load encounter
        try:
            enc = Encounter.objects.select_related("patient", "department").get(
                pk=encounter_id, is_deleted=False
            )
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        vitals = data.get("vitals") or {}
        symptoms = data.get("symptoms") or []
        red_flags = data.get("red_flags") or {}
        raw_input_text = data.get("raw_input_text", "")

        # LLM pre-processing (feature-flagged, PHI-sanitized)
        llm_result = None
        if raw_input_text and request.feature_flags.get("LLM_ENABLED"):
            llm_result = self._call_llm_parse(raw_input_text, enc, request.feature_flags)
            if llm_result:
                # Merge LLM parsed fields into inputs — nurse confirmation assumed
                vitals = {**llm_result.get("vitals", {}), **vitals}  # explicit fields override LLM
                symptoms = symptoms or llm_result.get("symptoms", [])
                red_flags = red_flags or {rf: True for rf in llm_result.get("red_flags", [])}

        # Persist raw_input_text to triagedata
        if raw_input_text:
            TriageData.objects.update_or_create(
                encounter=enc,
                defaults={"raw_input_text": raw_input_text, "llm_processed_json": llm_result},
            )

        # Run deterministic triage engine
        from triage.engine import compute_triage
        result = compute_triage(
            encounter_id=str(enc.id),
            vitals=vitals,
            symptoms=symptoms,
            red_flags=red_flags,
            patient_age=enc.patient.age,
            request=request,
        )

        # Generate LLM explanation text (optional, display only)
        explanation_text = self._build_explanation(result, vitals, request.feature_flags)

        # Reload updated encounter for response
        enc.refresh_from_db()

        return ok({
            "encounter_id": str(enc.id),
            "priority": result["priority"],
            "risk_score": result["risk_score"],
            "effective_score": result["effective_score"],
            "aging_bonus": result.get("aging_bonus", 0),
            "confidence_score": result["confidence_score"],
            "reasons": result["reasons"],
            "hard_override": result.get("hard_override", False),
            "explanation_text": explanation_text,
            "assigned_doctor_id": str(enc.assigned_doctor_id) if enc.assigned_doctor_id else None,
            # Explainability panel fields
            "vitals_panel": result.get("vitals_panel", []),
            "symptoms_contribution": result.get("symptoms_contribution", []),
            "risk_factors": result.get("risk_factors", []),
            "final_priority_explanation": result.get("final_priority_explanation", explanation_text),
            "explainability": result.get("explainability"),
            "triage": result.get("triage"),
            "risk_prediction": result.get("risk_prediction"),
        })

    def _call_llm_parse(self, raw_text: str, enc, feature_flags: dict) -> dict | None:
        """Parse unstructured text via GROQ (Hinglish -> JSON)."""
        from llm_sidecar.sanitizer import sanitize_for_llm, verify_no_phi_leaked
        from llm_sidecar.client import call_groq_json
        from llm_sidecar.prompts import HINGLISH_TO_JSON_PROMPT
        from core.audit import log_audit

        triage_dict = {"raw_input_text": raw_text, "vitals_json": {}, "symptoms_json": []}
        patient_dict = {"age": enc.patient.age, "gender": enc.patient.gender}
        sanitized = sanitize_for_llm(triage_dict, patient_dict)

        if not verify_no_phi_leaked(sanitized):
            logger.warning("PHI check failed — LLM call blocked for encounter %s", enc.id)
            return None

        result = call_groq_json(
            HINGLISH_TO_JSON_PROMPT,
            f"Parse this: {raw_text}",
            feature_flags,
            expected_keys=["symptoms", "vitals"],
        )

        log_audit("llm.parse", "encounter", enc.id, None, None, None, None,
                  metadata={"sanitized_input": sanitized, "llm_success": result is not None})
        return result

    def _build_explanation(self, result: dict, vitals: dict, feature_flags: dict) -> str:
        """Build explanation text — prefer LLM formatting, fallback to deterministic."""
        missing_vitals = [f for f in ["hr", "spo2", "bp_systolic"] if not vitals.get(f)]
        missing_str = ", ".join(missing_vitals) if missing_vitals else "none"
        reasons_str = "; ".join(result["reasons"][:3]) if result["reasons"] else "see vitals"

        if feature_flags.get("LLM_ENABLED") and result["reasons"]:
            from llm_sidecar.client import call_groq
            from llm_sidecar.prompts import EXPLANATION_FORMAT_PROMPT
            prompt_filled = EXPLANATION_FORMAT_PROMPT.format(
                priority=result["priority"].upper(),
                score=result["effective_score"],
                confidence=result["confidence_score"],
                reasons=reasons_str,
                missing=missing_str,
            )
            text = call_groq("You produce concise clinical summaries.", prompt_filled, feature_flags, max_tokens=100)
            if text:
                return text.strip()

        # Deterministic fallback
        missing_note = f" (missing: {missing_str})" if missing_vitals else ""
        return (
            f"{result['priority'].upper()} priority (score {result['effective_score']}) — "
            f"{reasons_str}. Confidence {result['confidence_score']}%{missing_note}."
        )

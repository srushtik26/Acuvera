"""
AI Clinical Insight Engine.
POST /api/encounters/{id}/insight/
Returns differential diagnoses + investigation suggestions via GROQ.
Results cached on Encounter.ai_insight_json — second call returns cache instantly.
"""
import random
import logging
from django.utils import timezone
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsDoctor
from core.models import Encounter

logger = logging.getLogger("acuvera.insight")

# Deterministic fallback: symptom/vital → likely differentials + investigations
RULE_BASED_INSIGHTS = {
    "chest_pain": {
        "differentials": [
            {"condition": "Acute Coronary Syndrome", "confidence": "high",
             "reason": "Chest pain with diaphoresis and tachycardia are classic ACS indicators; myocardial ischemia must be ruled out immediately."},
            {"condition": "Pulmonary Embolism", "confidence": "medium",
             "reason": "Chest pain with hypoxia and tachycardia may indicate pulmonary thromboembolism."},
            {"condition": "Aortic Dissection", "confidence": "medium",
             "reason": "Severe chest pain, especially with BP differential between arms, may suggest aortic dissection."},
        ],
        "investigations": [
            {"name": "12-lead ECG", "reason": "Identifies ischemia, STEMI, or arrhythmia patterns immediately."},
            {"name": "Troponin I/T (stat)", "reason": "Detects myocardial injury — elevated in ACS."},
            {"name": "Chest X-Ray", "reason": "Rules out pneumothorax, aortic widening, or pulmonary edema."},
            {"name": "D-Dimer", "reason": "Screens for pulmonary embolism if clinically suspected."},
            {"name": "Echo if available", "reason": "Assesses wall motion abnormalities and cardiac function."},
        ],
    },
    "shortness_of_breath": {
        "differentials": [
            {"condition": "Pneumonia / LRTI", "confidence": "high",
             "reason": "Respiratory distress with fever and low SpO2 suggests lower respiratory tract infection."},
            {"condition": "Acute Pulmonary Edema", "confidence": "medium",
             "reason": "SOB with crackles, low SpO2, and tachycardia may indicate cardiac decompensation."},
            {"condition": "COPD Exacerbation", "confidence": "medium",
             "reason": "Tachypnea and hypoxia in older patients with smoking history suggest COPD flare."},
        ],
        "investigations": [
            {"name": "Chest X-Ray", "reason": "Identifies consolidation, effusion, or pulmonary edema pattern."},
            {"name": "SpO2 monitoring", "reason": "Continuous oxygen saturation monitoring is essential."},
            {"name": "ABG", "reason": "Arterial blood gas quantifies respiratory failure severity."},
            {"name": "CBC with differential", "reason": "Leukocytosis suggests infectious cause."},
            {"name": "BNP/Pro-BNP", "reason": "Elevated BNP indicates cardiac cause of dyspnea."},
        ],
    },
    "stroke_symptoms": {
        "differentials": [
            {"condition": "Ischemic Stroke", "confidence": "high",
             "reason": "Sudden focal neurological deficit is highly suggestive of ischemic cerebrovascular event requiring urgent intervention."},
            {"condition": "Hemorrhagic Stroke", "confidence": "medium",
             "reason": "Severe headache with neurological deficit may indicate intracranial hemorrhage."},
            {"condition": "TIA", "confidence": "medium",
             "reason": "Transient neurological symptoms with full resolution may represent TIA with high stroke risk."},
        ],
        "investigations": [
            {"name": "Non-contrast CT Head (urgent)", "reason": "Differentiates ischemic from hemorrhagic stroke — time-critical."},
            {"name": "Blood glucose", "reason": "Hypoglycemia can mimic stroke and must be excluded immediately."},
            {"name": "INR/PT", "reason": "Guides thrombolysis eligibility in ischemic stroke."},
            {"name": "ECG for AF", "reason": "Atrial fibrillation is a major cause of cardioembolic stroke."},
            {"name": "BP both arms", "reason": "Asymmetric BP may suggest aortic dissection affecting cerebral perfusion."},
        ],
    },
    "trauma": {
        "differentials": [
            {"condition": "Traumatic Brain Injury", "confidence": "medium",
             "reason": "Head trauma with altered GCS requires urgent neurological evaluation."},
            {"condition": "Internal Hemorrhage", "confidence": "medium",
             "reason": "Hypotension and tachycardia following trauma suggests internal bleeding."},
            {"condition": "Fracture", "confidence": "high",
             "reason": "Mechanical trauma with localized pain and swelling is consistent with fracture."},
        ],
        "investigations": [
            {"name": "FAST ultrasound", "reason": "Rapid bedside assessment for intra-abdominal free fluid."},
            {"name": "CT scan (trauma protocol)", "reason": "Comprehensive imaging to identify occult injuries."},
            {"name": "CBC", "reason": "Assesses for hemorrhage via hemoglobin levels."},
            {"name": "Cross-match blood", "reason": "Prepares for potential transfusion in hemorrhagic shock."},
            {"name": "X-Ray affected region", "reason": "Confirms fracture or dislocation."},
        ],
    },
    "seizure": {
        "differentials": [
            {"condition": "Epileptic Seizure", "confidence": "high",
             "reason": "Known epilepsy or typical generalized convulsions strongly suggest epileptic etiology."},
            {"condition": "Hypoglycemia", "confidence": "medium",
             "reason": "Hypoglycemia can present with seizure-like activity — always exclude first."},
            {"condition": "Meningitis/Encephalitis", "confidence": "low",
             "reason": "Fever with seizure and neck stiffness raises concern for CNS infection."},
        ],
        "investigations": [
            {"name": "Blood glucose (stat)", "reason": "Hypoglycemia must be excluded immediately as a reversible cause."},
            {"name": "Electrolytes", "reason": "Hyponatremia and hypomagnesemia are common seizure triggers."},
            {"name": "CT Head", "reason": "Excludes structural cause especially in first seizure."},
            {"name": "LP if fever present", "reason": "Lumbar puncture rules out meningitis when fever accompanies seizure."},
            {"name": "EEG if available", "reason": "Confirms epileptiform activity and guides treatment."},
        ],
    },
    "syncope": {
        "differentials": [
            {"condition": "Vasovagal Syncope", "confidence": "high",
             "reason": "Precipitating trigger + prodrome + rapid recovery is classic for vasovagal mechanism."},
            {"condition": "Cardiac Arrhythmia", "confidence": "medium",
             "reason": "Sudden loss of consciousness without prodrome may indicate arrhythmic etiology."},
            {"condition": "Orthostatic Hypotension", "confidence": "medium",
             "reason": "Syncope on standing with BP drop suggests volume depletion or autonomic failure."},
        ],
        "investigations": [
            {"name": "ECG", "reason": "Identifies arrhythmia, long QT, or Brugada pattern."},
            {"name": "Orthostatic BP measurements", "reason": "Confirms postural hypotension as cause."},
            {"name": "Blood glucose", "reason": "Excludes hypoglycemia as syncope cause."},
            {"name": "CBC", "reason": "Anemia may cause syncopal episodes."},
            {"name": "Echo if cardiac suspected", "reason": "Structural cardiac pathology such as AS may cause exertional syncope."},
        ],
    },
    "severe_abdominal_pain": {
        "differentials": [
            {"condition": "Appendicitis", "confidence": "medium",
             "reason": "Right lower quadrant pain with fever and leukocytosis suggests appendicitis."},
            {"condition": "Peptic Ulcer Perforation", "confidence": "medium",
             "reason": "Sudden severe epigastric pain with peritoneal signs suggests perforation."},
            {"condition": "Mesenteric Ischemia", "confidence": "low",
             "reason": "Severe pain out of proportion to exam in elderly/vascular patient suggests mesenteric ischemia."},
        ],
        "investigations": [
            {"name": "Abdominal ultrasound", "reason": "First-line imaging for abdominal pain — identifies free fluid and organ pathology."},
            {"name": "CBC", "reason": "Leukocytosis supports infectious or inflammatory cause."},
            {"name": "CRP/ESR", "reason": "Elevated inflammatory markers support acute abdominal pathology."},
            {"name": "Urinalysis", "reason": "Excludes renal colic or urinary tract infection."},
            {"name": "Upright abdominal X-Ray", "reason": "Free air under diaphragm indicates perforation."},
        ],
    },
    "altered_mental_status": {
        "differentials": [
            {"condition": "Metabolic Encephalopathy", "confidence": "high",
             "reason": "Altered consciousness with metabolic derangements (glucose, sodium, renal failure) is most common AMS cause."},
            {"condition": "Sepsis", "confidence": "medium",
             "reason": "Fever, altered GCS, and hemodynamic instability suggest septic encephalopathy."},
            {"condition": "Intracranial Event", "confidence": "medium",
             "reason": "Focal deficits or sudden onset AMS requires structural intracranial cause to be excluded."},
        ],
        "investigations": [
            {"name": "Blood glucose (stat)", "reason": "Hypoglycemia is the most common reversible AMS cause."},
            {"name": "Electrolytes", "reason": "Hyponatremia and uremia commonly cause encephalopathy."},
            {"name": "Sepsis workup (cultures/lactate)", "reason": "Blood cultures and lactate identify sepsis as AMS etiology."},
            {"name": "CT Head", "reason": "Rules out stroke, hemorrhage, or mass lesion."},
            {"name": "Urinalysis", "reason": "UTI is a common precipitant of AMS especially in elderly."},
        ],
    },
}

DEFAULT_INSIGHT = {
    "differentials": [
        {"condition": "Clinical assessment required", "confidence": "low"},
    ],
    "investigations": ["Full vital sign monitoring", "CBC", "BMP", "Urinalysis"],
}

DISCLAIMER = (
    "⚠️ AI-generated suggestion only. Not a clinical diagnosis. "
    "All decisions must be made by the treating physician."
)


def _deterministic_insight(symptoms: list, vitals: dict) -> dict:
    """Rule-based fallback — match first known symptom pattern."""
    symptoms_lower = [s.lower().replace(" ", "_") for s in (symptoms or [])]

    # Priority order of symptom matching
    priority_symptoms = [
        "chest_pain", "stroke_symptoms", "seizure", "altered_mental_status",
        "shortness_of_breath", "trauma", "syncope", "severe_abdominal_pain"
    ]

    for key in priority_symptoms:
        if key in symptoms_lower:
            insight = RULE_BASED_INSIGHTS[key].copy()
            insight["source"] = "rule_based"
            insight["disclaimer"] = DISCLAIMER
            return insight

    # Vital-based fallback
    if vitals:
        spo2 = vitals.get("spo2")
        hr = vitals.get("hr")
        if spo2 and spo2 < 92:
            return {**RULE_BASED_INSIGHTS["shortness_of_breath"],
                    "source": "rule_based", "disclaimer": DISCLAIMER}
        if hr and hr > 140:
            return {**RULE_BASED_INSIGHTS["chest_pain"],
                    "source": "rule_based", "disclaimer": DISCLAIMER}

    return {**DEFAULT_INSIGHT, "source": "rule_based", "disclaimer": DISCLAIMER}


class InsightView(APIView):
    """POST /api/encounters/{pk}/insight/"""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            enc = Encounter.objects.select_related(
                "patient", "department"
            ).get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        # Return cached insight if available
        if enc.ai_insight_json:
            logger.info("Returning cached AI insight for encounter %s", pk)
            return ok({**enc.ai_insight_json, "cached": True})

        # Load triage data
        vitals, symptoms = {}, []
        try:
            td = enc.triage_data
            vitals = td.vitals_json or {}
            symptoms = td.symptoms_json or []
        except Exception:
            pass

        # Try LLM first
        insight = None
        if request.feature_flags.get("LLM_ENABLED"):
            insight = self._call_llm_insight(enc, vitals, symptoms, request.feature_flags)

        # Fallback if no LLM (or LLM fails)
        if not insight:
            insight = _deterministic_insight(symptoms, vitals)
            logger.info("Using rule-based insight fallback for encounter %s", pk)

        insight["disclaimer"] = DISCLAIMER

        # Add risk prediction
        try:
            from triage.risk_model import compute_risk_prediction
            insight["risk_prediction"] = compute_risk_prediction(vitals, symptoms, enc.patient.age, enc.risk_score)
        except Exception as e:
            logger.error("Risk prediction failed for insight %s: %s", pk, e)

        # Cache on the encounter
        enc.ai_insight_json = insight
        enc.save(update_fields=["ai_insight_json"])

        return ok({**insight, "cached": False})

    def _call_llm_insight(self, enc, vitals: dict, symptoms: list, feature_flags: dict) -> dict | None:
        try:
            from llm_sidecar.client import call_groq_json
            from llm_sidecar.prompts import CLINICAL_INSIGHT_PROMPT
            from llm_sidecar.sanitizer import sanitize_for_llm

            triage_dict = {"vitals_json": vitals, "symptoms_json": symptoms}
            patient_dict = {"age": enc.patient.age, "gender": enc.patient.gender}
            sanitized = sanitize_for_llm(triage_dict, patient_dict)

            user_content = (
                f"Patient: {sanitized.get('age_group', 'unknown age')} {sanitized.get('gender', '')}\n"
                f"Vitals: {sanitized.get('vitals', {})}\n"
                f"Symptoms: {', '.join(sanitized.get('symptoms', []) or [])}\n"
                f"Generate differential diagnosis and investigation suggestions."
            )

            result = call_groq_json(
                CLINICAL_INSIGHT_PROMPT,
                user_content,
                feature_flags,
                expected_keys=["differentials", "investigations"],
                max_tokens=400,
            )

            if result:
                result["source"] = "llm"
                logger.info("LLM clinical insight success for encounter %s", enc.id)
                return result

        except Exception as e:
            logger.warning("LLM insight failed for encounter %s: %s — using fallback", enc.id, e)

        return None

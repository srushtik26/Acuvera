"""
Acuvera Triage Engine — fully deterministic, no LLM influence.
See SPEC.md §6.A for the exact algorithm specification.
"""
import logging
import math
from datetime import timezone
from typing import Optional

from django.db import transaction
from django.utils import timezone as dj_tz

from core.audit import log_audit, model_snapshot
from triage.risk_model import compute_risk_prediction

logger = logging.getLogger("acuvera.triage.engine")

# -------------------------------------------------------------------
# Constants (configurable via department.priority_weight_config)
# -------------------------------------------------------------------
MAX_RISK_SCORE = 100
DEFAULT_CRITICAL_GCS = 8
DEFAULT_CRITICAL_SPO2 = 85
DEFAULT_AGING_MINUTES_UNIT = 10
DEFAULT_AGING_POINT_UNIT = 5
DEFAULT_MIN_COMPLETE_RATIO = 0.6
DEFAULT_LOW_COMPLETENESS_PENALTY = 10

# Required vitals fields for completeness calculation
REQUIRED_VITALS = ["hr", "spo2"]
REQUIRED_SYMPTOMS = True  # at least one symptom required for full completeness


def _required_fields_present(vitals: dict, symptoms: list) -> int:
    """Count how many of the required fields are present (non-null)."""
    total_required = len(REQUIRED_VITALS) + 1  # +1 for symptoms
    present = 0
    for field in REQUIRED_VITALS:
        if vitals.get(field) is not None:
            present += 1
    # Optional additional vitals add to completeness
    optional_vitals = ["bp_systolic", "bp_diastolic", "temp", "rr", "gcs", "pain_score"]
    total_required += len(optional_vitals)
    for field in optional_vitals:
        if vitals.get(field) is not None:
            present += 1
    if symptoms:
        present += 1
    return present, total_required


def compute_completeness(vitals: dict, symptoms: list) -> float:
    """Return a ratio 0.0–1.0 of how complete the triage data is."""
    vitals = vitals or {}
    symptoms = symptoms or []
    present, total = _required_fields_present(vitals, symptoms)
    return min(1.0, present / total if total > 0 else 0.0)


def _check_hard_overrides(red_flags: dict, vitals: dict, dept_config: dict) -> Optional[str]:
    """
    Return the override reason if a hard override applies, else None.
    Hard overrides immediately set priority to critical, score to MAX.
    """
    red_flags = red_flags or {}
    vitals = vitals or {}

    if red_flags.get("cardiac_arrest"):
        return "Hard override: cardiac arrest flag"
    if red_flags.get("no_pulse"):
        return "Hard override: no pulse detected"
    if red_flags.get("severe_hemorrhage"):
        return "Hard override: severe hemorrhage (active external bleeding)"
    if red_flags.get("airway_compromised"):
        return "Hard override: airway compromised"

    critical_gcs = dept_config.get("critical_gcs_threshold", DEFAULT_CRITICAL_GCS)
    gcs = vitals.get("gcs")
    if gcs is not None and gcs <= critical_gcs:
        return f"Hard override: GCS {gcs} ≤ threshold ({critical_gcs})"

    critical_spo2 = dept_config.get("critical_spo2_threshold", DEFAULT_CRITICAL_SPO2)
    spo2 = vitals.get("spo2")
    if spo2 is not None and spo2 < critical_spo2:
        return f"Hard override: SpO2 {spo2}% < critical threshold ({critical_spo2}%)"

    return None


def _evaluate_weighted_conditions(vitals: dict, symptoms: list, patient_age: Optional[int], dept_config: dict) -> tuple:
    """
    Evaluate all configured weight conditions. Returns (score, reasons_list).
    """
    vitals = vitals or {}
    symptoms = symptoms or []
    score = 0
    reasons = []

    # SpO2 low — WHO clinical threshold: < 92% is clinically significant hypoxia
    spo2_threshold = dept_config.get("SpO2_low_threshold", 92)
    spo2_weight = dept_config.get("SpO2_low", 20)
    if vitals.get("spo2") is not None and vitals["spo2"] < spo2_threshold:
        score += spo2_weight
        reasons.append(f"SpO2 below threshold ({vitals['spo2']}% < {spo2_threshold}%)")

    # Heart rate high — tachycardia threshold (clinical: > 110 warrants attention)
    hr_threshold = dept_config.get("HR_high_threshold", 110)
    hr_weight = dept_config.get("HR_high", 15)
    if vitals.get("hr") is not None and vitals["hr"] > hr_threshold:
        score += hr_weight
        reasons.append(f"HR elevated ({vitals['hr']} > {hr_threshold} bpm)")

    # Heart rate low (bradycardia) — symptomatic bradycardia < 55
    hr_low_threshold = dept_config.get("HR_low_threshold", 55)
    hr_low_weight = dept_config.get("HR_low", 15)
    if vitals.get("hr") is not None and vitals["hr"] < hr_low_threshold:
        score += hr_low_weight
        reasons.append(f"HR critically low ({vitals['hr']} < {hr_low_threshold} bpm)")

    # Hypertension
    bp_high_threshold = dept_config.get("BP_high_threshold", 180)
    bp_weight = dept_config.get("BP_high", 10)
    if vitals.get("bp_systolic") is not None and vitals["bp_systolic"] >= bp_high_threshold:
        score += bp_weight
        reasons.append(f"BP severely elevated ({vitals['bp_systolic']}/{vitals.get('bp_diastolic', '?')} mmHg)")

    # Hypotension — systolic < 90 mmHg is shock territory
    bp_low_threshold = dept_config.get("BP_low_threshold", 90)
    bp_low_weight = dept_config.get("BP_low", 20)
    if vitals.get("bp_systolic") is not None and vitals["bp_systolic"] < bp_low_threshold:
        score += bp_low_weight
        reasons.append(f"Hypotension — BP {vitals['bp_systolic']}/{vitals.get('bp_diastolic', '?')} mmHg (systolic < {bp_low_threshold})")

    # Severe pain — lowered to 7 for better sensitivity
    pain_threshold = dept_config.get("pain_threshold", 7)
    pain_weight = dept_config.get("severe_pain", 10)
    if vitals.get("pain_score") is not None and vitals["pain_score"] >= pain_threshold:
        score += pain_weight
        reasons.append(f"Severe pain reported (score {vitals['pain_score']}/10)")

    # Respiratory rate high — tachypnea threshold: > 24/min
    rr_threshold = dept_config.get("RR_high_threshold", 24)
    rr_weight = dept_config.get("RR_high", 15)
    if vitals.get("rr") is not None and vitals["rr"] > rr_threshold:
        score += rr_weight
        reasons.append(f"Respiratory rate high ({vitals['rr']} > {rr_threshold} /min)")

    # Fever — lowered to 101°F for febrile detection
    temp_threshold = dept_config.get("temp_high_threshold", 101.0)
    temp_weight = dept_config.get("temp_high", 10)
    if vitals.get("temp") is not None and vitals["temp"] >= temp_threshold:
        score += temp_weight
        reasons.append(f"Fever ({vitals['temp']}°F ≥ {temp_threshold}°F)")

    # Age > 60 (higher risk)
    age_weight = dept_config.get("age_over_60", 5)
    if patient_age is not None and patient_age >= 60:
        score += age_weight
        reasons.append(f"Age ≥ 60 (risk factor: {patient_age} years)")

    # Symptom-based weights
    symptom_weights = {
        "chest_pain": ("chest_pain", 20, "Chest pain reported"),
        "sweating": ("sweating", 5, "Diaphoresis/sweating reported"),
        "syncope": ("syncope", 15, "Syncope/fainting reported"),
        "altered_mental_status": ("altered_mental_status", 15, "Altered mental status"),
        "severe_headache": ("severe_headache", 10, "Severe headache"),
        "shortness_of_breath": ("shortness_of_breath", 15, "Shortness of breath"),
        "seizure": ("seizure", 15, "Seizure reported"),
        "stroke_symptoms": ("stroke_symptoms", 20, "Stroke symptoms reported"),
        "severe_abdominal_pain": ("severe_abdominal_pain", 10, "Severe abdominal pain"),
        "trauma": ("trauma", 15, "Significant trauma"),
    }
    symptoms_lower = [s.lower().replace(" ", "_") for s in symptoms]
    for key, (symptom_key, default_weight, label) in symptom_weights.items():
        weight = dept_config.get(f"symptom_{key}", default_weight)
        if symptom_key in symptoms_lower:
            score += weight
            reasons.append(label)

    return score, reasons


# Clinical signal mapping for symptoms
SYMPTOM_CLINICAL_SIGNALS = {
    "chest_pain": "Cardiac risk indicator — potential ischemia or ACS",
    "sweating": "Diaphoresis — autonomic stress response, ACS indicator",
    "syncope": "Transient loss of consciousness — neurological/cardiac concern",
    "altered_mental_status": "CNS dysfunction — sepsis, metabolic, or intracranial event",
    "severe_headache": "May indicate intracranial hypertension or subarachnoid hemorrhage",
    "shortness_of_breath": "Respiratory distress — potential hypoxia or cardiac decompensation",
    "seizure": "CNS instability — epilepsy, hypoglycemia, or intracranial event",
    "stroke_symptoms": "Potential cerebrovascular event — time-critical intervention needed",
    "severe_abdominal_pain": "May indicate peritonitis, ischemia, or visceral perforation",
    "trauma": "Mechanical injury — internal hemorrhage or fracture risk",
}


def build_symptoms_contribution(symptoms: list) -> list:
    """
    Return list of {symptom, clinical_signal} for each recognized symptom.
    For display in triage explainability panel.
    """
    symptoms_lower = [s.lower().replace(" ", "_") for s in (symptoms or [])]
    result = []
    for s in symptoms_lower:
        signal = SYMPTOM_CLINICAL_SIGNALS.get(s)
        if signal:
            result.append({
                "symptom": s.replace("_", " ").title(),
                "clinical_signal": signal,
            })
        elif s:
            result.append({
                "symptom": s.replace("_", " ").title(),
                "clinical_signal": "Reported by patient/nurse",
            })
    return result


def build_risk_factors_panel(reasons: list, vitals: dict, symptoms: list,
                              patient_age, dept_config: dict, aging_bonus: int = 0) -> list:
    """
    Build structured risk factor list with point contributions.
    Each entry: {factor, points, category}
    """
    vitals = vitals or {}
    dept_config = dept_config or {}
    factors = []

    spo2 = vitals.get("spo2")
    spo2_threshold = dept_config.get("SpO2_low_threshold", 92)
    if spo2 is not None and spo2 < spo2_threshold:
        pts = dept_config.get("SpO2_low", 20)
        suffix = "Severe hypoxia" if spo2 < 85 else "Hypoxia"
        factors.append({"factor": f"SpO₂ {spo2}% < {spo2_threshold}% — {suffix}", "points": f"+{pts}", "category": "vital"})

    hr = vitals.get("hr")
    if hr is not None:
        hr_high = dept_config.get("HR_high_threshold", 110)
        if hr > hr_high:
            pts = dept_config.get("HR_high", 15)
            factors.append({"factor": f"Tachycardia HR {hr} > {hr_high} bpm", "points": f"+{pts}", "category": "vital"})
        hr_low = dept_config.get("HR_low_threshold", 55)
        if hr < hr_low:
            pts = dept_config.get("HR_low", 15)
            factors.append({"factor": f"Bradycardia HR {hr} < {hr_low} bpm", "points": f"+{pts}", "category": "vital"})

    sbp = vitals.get("bp_systolic")
    if sbp is not None:
        bp_low = dept_config.get("BP_low_threshold", 90)
        bp_high = dept_config.get("BP_high_threshold", 180)
        if sbp < bp_low:
            pts = dept_config.get("BP_low", 20)
            factors.append({"factor": f"Hypotension BP {sbp} mmHg < {bp_low}", "points": f"+{pts}", "category": "vital"})
        elif sbp >= bp_high:
            pts = dept_config.get("BP_high", 10)
            factors.append({"factor": f"Hypertensive emergency BP {sbp} mmHg", "points": f"+{pts}", "category": "vital"})

    rr = vitals.get("rr")
    if rr is not None and rr > dept_config.get("RR_high_threshold", 24):
        pts = dept_config.get("RR_high", 15)
        factors.append({"factor": f"Tachypnea RR {rr}/min", "points": f"+{pts}", "category": "vital"})

    temp = vitals.get("temp")
    if temp is not None and temp >= dept_config.get("temp_high_threshold", 101.0):
        pts = dept_config.get("temp_high", 10)
        factors.append({"factor": f"Fever {temp}°F", "points": f"+{pts}", "category": "vital"})

    pain = vitals.get("pain_score")
    if pain is not None and pain >= dept_config.get("pain_threshold", 7):
        pts = dept_config.get("severe_pain", 10)
        factors.append({"factor": f"Severe pain score {pain}/10", "points": f"+{pts}", "category": "vital"})

    # Symptom factors
    symptom_pt_map = {
        "chest_pain": (20, "symptom"),
        "sweating": (5, "symptom"),
        "syncope": (15, "symptom"),
        "altered_mental_status": (15, "symptom"),
        "severe_headache": (10, "symptom"),
        "shortness_of_breath": (15, "symptom"),
        "seizure": (15, "symptom"),
        "stroke_symptoms": (20, "symptom"),
        "severe_abdominal_pain": (10, "symptom"),
        "trauma": (15, "symptom"),
    }
    symptoms_lower = [s.lower().replace(" ", "_") for s in (symptoms or [])]
    for sym, (default_pts, cat) in symptom_pt_map.items():
        if sym in symptoms_lower:
            pts = dept_config.get(f"symptom_{sym}", default_pts)
            factors.append({"factor": f"{sym.replace('_', ' ').title()} symptom", "points": f"+{pts}", "category": cat})

    # Age factor
    if patient_age is not None and patient_age >= 60:
        pts = dept_config.get("age_over_60", 5)
        factors.append({"factor": f"Age ≥ 60 ({patient_age} years)", "points": f"+{pts}", "category": "demographic"})

    # Aging (wait time) bonus
    if aging_bonus > 0:
        factors.append({"factor": f"Extended wait time bonus", "points": f"+{aging_bonus}", "category": "operational"})

    return factors


def _map_score_to_priority(score: int) -> str:
    if score >= 71:
        return "critical"
    elif score >= 41:
        return "high"
    elif score >= 21:
        return "moderate"
    else:
        return "low"


def compute_triage(encounter_id: str, vitals: dict, symptoms: list, red_flags: dict,
                   patient_age: Optional[int] = None, request=None) -> dict:
    """
    Main entry point for the triage engine.
    Atomic transaction with SELECT FOR UPDATE — prevents concurrent analyze calls.

    Returns a dict with: priority, risk_score, effective_score, confidence_score, reasons.
    """
    from core.models import Encounter, TriageData

    with transaction.atomic():
        enc = Encounter.objects.select_for_update().get(pk=encounter_id)
        dept_config = enc.department.priority_weight_config or {}

        # Step 1: Completeness
        completeness = compute_completeness(vitals, symptoms)

        # Step 2: Hard overrides
        override_reason = _check_hard_overrides(red_flags, vitals, dept_config)
        if override_reason:
            confidence = min(100, int(80 + completeness * 20))
            pre = model_snapshot(enc)
            enc.priority = "critical"
            enc.risk_score = MAX_RISK_SCORE
            enc.confidence_score = confidence
            enc.version += 1
            enc.save()

            _upsert_triage_data(enc, vitals, symptoms, red_flags, completeness)

            log_audit("triage.analyze", "encounter", enc.id, None, pre, model_snapshot(enc), request,
                      metadata={"override": override_reason})
            logger.info("Hard override triggered for encounter %s: %s", encounter_id, override_reason)

            vitals_panel = build_vitals_panel(vitals, dept_config)
            symptoms_contribution = build_symptoms_contribution(symptoms)
            
            try:
                risk_prediction = compute_risk_prediction(vitals, symptoms, patient_age, MAX_RISK_SCORE)
            except Exception as e:
                logger.error("Risk prediction failed for encounter %s: %s", encounter_id, e)
                risk_prediction = None

            return {
                "encounter_id": str(enc.id),
                "priority": "critical",
                "risk_score": MAX_RISK_SCORE,
                "effective_score": MAX_RISK_SCORE,
                "confidence_score": confidence,
                "reasons": [override_reason],
                "hard_override": True,
                "vitals_panel": vitals_panel,
                "symptoms_contribution": symptoms_contribution,
                "risk_factors": [{"factor": override_reason, "points": f"+{MAX_RISK_SCORE}", "category": "override"}],
                "final_priority_explanation": (
                    f"CRITICAL — Hard override triggered: {override_reason}. "
                    f"Immediate resuscitation or physician evaluation required."
                ),
                "triage": {
                    "priority": "critical",
                    "risk_score": MAX_RISK_SCORE,
                    "effective_score": MAX_RISK_SCORE,
                    "confidence_score": confidence,
                    "reasons": [override_reason],
                },
                "explainability": {
                    "vitals_panel": vitals_panel,
                    "symptoms_contribution": symptoms_contribution,
                    "risk_factors": [{"factor": override_reason, "points": f"+{MAX_RISK_SCORE}", "category": "override"}],
                    "final_priority_explanation": (
                        f"CRITICAL — Hard override triggered: {override_reason}. "
                        f"Immediate resuscitation or physician evaluation required."
                    ),
                },
                "risk_prediction": risk_prediction,
            }

        # Step 3: Weighted scoring
        base_score, reasons = _evaluate_weighted_conditions(vitals, symptoms, patient_age, dept_config)

        # Step 4: Aging bonus
        aging_minutes_unit = dept_config.get("aging_minutes_unit", DEFAULT_AGING_MINUTES_UNIT)
        aging_point_unit = dept_config.get("aging_point_unit", DEFAULT_AGING_POINT_UNIT)
        minutes_waited = (dj_tz.now() - enc.created_at).total_seconds() / 60.0
        aging_bonus = math.floor(minutes_waited / aging_minutes_unit) * aging_point_unit
        MAX_AGING_BONUS = 40
        aging_bonus = min(MAX_AGING_BONUS, aging_bonus)
        if aging_bonus > 0:
            reasons.append(f"Waiting time bonus: +{aging_bonus} pts ({minutes_waited:.0f} min waited)")

        effective_score = base_score + aging_bonus
        priority = _map_score_to_priority(effective_score)

        # Step 5: Confidence
        min_complete_ratio = dept_config.get("min_complete_ratio", DEFAULT_MIN_COMPLETE_RATIO)
        low_complete_penalty = dept_config.get("low_completeness_penalty", DEFAULT_LOW_COMPLETENESS_PENALTY)
        confidence = round(completeness * 100)
        if completeness < min_complete_ratio:
            confidence = max(0, confidence - low_complete_penalty)

        # Save
        pre = model_snapshot(enc)
        enc.priority = priority
        enc.risk_score = effective_score
        enc.confidence_score = confidence
        enc.version += 1
        enc.save()

        try:
            risk_prediction = compute_risk_prediction(vitals, symptoms, patient_age, effective_score)
        except Exception as e:
            logger.error("Risk prediction failed for encounter %s: %s", encounter_id, e)
            risk_prediction = None

        log_metadata = {"score": effective_score, "reasons": reasons}
        if risk_prediction:
            log_metadata["risk_prediction_summary"] = {
                "overall_risk": risk_prediction.get("overall_deterioration_risk"),
                "risk_level": risk_prediction.get("risk_level")
            }

        _upsert_triage_data(enc, vitals, symptoms, red_flags, completeness)
        log_audit("triage.analyze", "encounter", enc.id, None, pre, model_snapshot(enc), request,
                  metadata=log_metadata)

        logger.info(
            "Triage complete encounter=%s priority=%s score=%d confidence=%d reasons=%d",
            encounter_id, priority, effective_score, confidence, len(reasons)
        )

        symptoms_contribution = build_symptoms_contribution(symptoms)
        risk_factors = build_risk_factors_panel(reasons, vitals, symptoms, patient_age, dept_config, aging_bonus)
        vitals_panel = build_vitals_panel(vitals, dept_config)

        # Build final explanation string
        top_reasons = "; ".join(reasons[:3]) if reasons else "clinical assessment required"
        final_explanation = (
            f"{priority.upper()} priority (score {effective_score}) — {top_reasons}. "
            f"Confidence {confidence}%."
        )
        if priority == "critical":
            final_explanation += " Immediate physician evaluation required."
        elif priority == "high":
            final_explanation += " Urgent assessment needed within 10 minutes."
        elif priority == "moderate":
            final_explanation += " Assess within 30 minutes."

        return {
            "encounter_id": str(enc.id),
            "priority": priority,
            "risk_score": base_score,
            "effective_score": effective_score,
            "aging_bonus": aging_bonus,
            "confidence_score": confidence,
            "reasons": reasons,
            "hard_override": False,
            "vitals_panel": vitals_panel,
            "symptoms_contribution": symptoms_contribution,
            "risk_factors": risk_factors,
            "final_priority_explanation": final_explanation,
            "triage": {
                "priority": priority,
                "risk_score": base_score,
                "effective_score": effective_score,
                "aging_bonus": aging_bonus,
                "confidence_score": confidence,
                "reasons": reasons,
            },
            "explainability": {
                "vitals_panel": vitals_panel,
                "symptoms_contribution": symptoms_contribution,
                "risk_factors": risk_factors,
                "final_priority_explanation": final_explanation,
            },
            "risk_prediction": risk_prediction,
        }


def _upsert_triage_data(enc, vitals, symptoms, red_flags, completeness):
    """Create or update the TriageData record for an encounter."""
    from core.models import TriageData
    TriageData.objects.update_or_create(
        encounter=enc,
        defaults={
            "vitals_json": vitals,
            "symptoms_json": symptoms,
            "red_flag_json": red_flags,
            "data_completeness_ratio": completeness,
        },
    )


def build_vitals_panel(vitals: dict, dept_config: dict = None) -> list:
    """
    Return a list of vital evaluations for display.
    Each entry: {vital, label, value, unit, status, note}
    status is one of: 'normal', 'borderline', 'critical'
    """
    if not vitals:
        return []

    dept_config = dept_config or {}
    panel = []

    # SpO2
    spo2 = vitals.get("spo2")
    if spo2 is not None:
        if spo2 >= 95:
            panel.append({"vital": "spo2", "label": "SpO₂", "value": spo2, "unit": "%",
                          "status": "normal", "note": "Normal"})
        elif spo2 >= 92:
            panel.append({"vital": "spo2", "label": "SpO₂", "value": spo2, "unit": "%",
                          "status": "borderline", "note": "Borderline — monitor closely"})
        else:
            panel.append({"vital": "spo2", "label": "SpO₂", "value": spo2, "unit": "%",
                          "status": "critical", "note": "Low — hypoxia risk"})

    # Heart rate
    hr = vitals.get("hr")
    if hr is not None:
        if 60 <= hr <= 100:
            panel.append({"vital": "hr", "label": "Heart Rate", "value": hr, "unit": "bpm",
                          "status": "normal", "note": "Normal sinus"})
        elif hr <= 110 and hr >= 55:
            panel.append({"vital": "hr", "label": "Heart Rate", "value": hr, "unit": "bpm",
                          "status": "borderline", "note": "Borderline — tachycardia trend" if hr > 100 else "Borderline — bradycardia trend"})
        elif hr > 110:
            panel.append({"vital": "hr", "label": "Heart Rate", "value": hr, "unit": "bpm",
                          "status": "critical", "note": "Tachycardia"})
        else:
            panel.append({"vital": "hr", "label": "Heart Rate", "value": hr, "unit": "bpm",
                          "status": "critical", "note": "Bradycardia"})

    # Blood pressure
    sbp = vitals.get("bp_systolic")
    dbp = vitals.get("bp_diastolic")
    if sbp is not None:
        bp_str = f"{sbp}/{dbp}" if dbp else str(sbp)
        if sbp < 90:
            panel.append({"vital": "bp", "label": "BP", "value": bp_str, "unit": "mmHg",
                          "status": "critical", "note": "Hypotension"})
        elif sbp >= 180:
            panel.append({"vital": "bp", "label": "BP", "value": bp_str, "unit": "mmHg",
                          "status": "critical", "note": "Hypertensive emergency"})
        elif sbp >= 140:
            panel.append({"vital": "bp", "label": "BP", "value": bp_str, "unit": "mmHg",
                          "status": "borderline", "note": "Stage 2 hypertension"})
        else:
            panel.append({"vital": "bp", "label": "BP", "value": bp_str, "unit": "mmHg",
                          "status": "normal", "note": "Acceptable range"})

    # Respiratory rate
    rr = vitals.get("rr")
    if rr is not None:
        if 12 <= rr <= 20:
            panel.append({"vital": "rr", "label": "Resp. Rate", "value": rr, "unit": "/min",
                          "status": "normal", "note": "Normal"})
        elif rr <= 24:
            panel.append({"vital": "rr", "label": "Resp. Rate", "value": rr, "unit": "/min",
                          "status": "borderline", "note": "Elevated — tachypnea threshold"})
        else:
            panel.append({"vital": "rr", "label": "Resp. Rate", "value": rr, "unit": "/min",
                          "status": "critical", "note": "Tachypnea"})

    # Temperature
    temp = vitals.get("temp")
    if temp is not None:
        if temp <= 99.5:
            panel.append({"vital": "temp", "label": "Temperature", "value": temp, "unit": "°F",
                          "status": "normal", "note": "Afebrile"})
        elif temp <= 101.0:
            panel.append({"vital": "temp", "label": "Temperature", "value": temp, "unit": "°F",
                          "status": "borderline", "note": "Low-grade fever"})
        else:
            panel.append({"vital": "temp", "label": "Temperature", "value": temp, "unit": "°F",
                          "status": "critical", "note": "Fever"})

    # GCS
    gcs = vitals.get("gcs")
    if gcs is not None:
        if gcs >= 14:
            panel.append({"vital": "gcs", "label": "GCS", "value": gcs, "unit": "",
                          "status": "normal", "note": "Alert"})
        elif gcs >= 9:
            panel.append({"vital": "gcs", "label": "GCS", "value": gcs, "unit": "",
                          "status": "borderline", "note": "Mild-moderate impairment"})
        else:
            panel.append({"vital": "gcs", "label": "GCS", "value": gcs, "unit": "",
                          "status": "critical", "note": "Severe impairment — hard override"})

    # Pain score
    pain = vitals.get("pain_score")
    if pain is not None:
        if pain <= 3:
            panel.append({"vital": "pain", "label": "Pain Score", "value": pain, "unit": "/10",
                          "status": "normal", "note": "Mild pain"})
        elif pain <= 6:
            panel.append({"vital": "pain", "label": "Pain Score", "value": pain, "unit": "/10",
                          "status": "borderline", "note": "Moderate pain"})
        else:
            panel.append({"vital": "pain", "label": "Pain Score", "value": pain, "unit": "/10",
                          "status": "critical", "note": "Severe pain"})

    return panel

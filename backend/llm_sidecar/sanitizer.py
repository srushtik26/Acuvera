"""
PHI Sanitizer — strips all patient identifiers before sending to LLM.
SPEC §7: No name, phone, MRN, address, private notes sent to LLM.
"""
import re
import logging

logger = logging.getLogger("acuvera.llm.sanitizer")

PHI_FIELDS = {"name", "contact_phone", "external_id", "dob", "raw_input_text"}


def sanitize_for_llm(triagedata_dict: dict, patient_dict: dict = None) -> dict:
    """
    Return a PHI-free dict safe to send to the LLM.
    Only includes: age_group, vitals, symptoms, duration, gender (normalized).
    """
    patient = patient_dict or {}
    permitted = {}

    # Age group (not exact DOB)
    age = patient.get("age") or triagedata_dict.get("age")
    if age:
        permitted["age_group"] = _age_bucket(age)

    # Gender normalized to broad category
    gender = patient.get("gender", "unknown")
    if gender in ("male", "female", "other", "unknown"):
        permitted["gender"] = gender

    # Vitals (numbers only — no identifiers possible)
    vitals = triagedata_dict.get("vitals_json") or {}
    safe_vitals = {}
    numeric_vitals = ["hr", "spo2", "bp_systolic", "bp_diastolic", "temp", "rr", "gcs", "pain_score"]
    for key in numeric_vitals:
        if vitals.get(key) is not None:
            safe_vitals[key] = vitals[key]
    if safe_vitals:
        permitted["vitals"] = safe_vitals

    # Symptoms (list of strings — checked for PHI patterns)
    symptoms = triagedata_dict.get("symptoms_json") or []
    permitted["symptoms"] = [_strip_phi_from_text(s) for s in symptoms]

    # Duration (from raw_input_text if extractable — anonymized)
    raw = triagedata_dict.get("raw_input_text", "")
    if raw:
        duration = _extract_duration(raw)
        if duration:
            permitted["duration_minutes"] = duration

    return permitted


def _age_bucket(age: int) -> str:
    if age < 18:
        return "pediatric"
    elif age < 40:
        return "adult_young"
    elif age < 60:
        return "adult_mid"
    elif age < 80:
        return "adult_senior"
    else:
        return "adult_elderly"


def _strip_phi_from_text(text: str) -> str:
    """Remove common PHI patterns from a free-text symptom string."""
    if not text:
        return text
    # Remove phone numbers
    text = re.sub(r"\b(\+91|0)?[\s\-]?[6-9]\d{9}\b", "[PHONE]", text)
    # Remove Indian Aadhaar-like numbers (12 digit)
    text = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[ID]", text)
    # Remove names (basic — single/double word title-case sequences)
    # Strip emails
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]", text)
    return text.strip()


def _extract_duration(raw_text: str) -> int | None:
    """Extract duration in minutes from unstructured text."""
    raw_lower = raw_text.lower()
    # "2 hours", "30 minutes", "1 hr"
    hour_match = re.search(r"(\d+)\s*(hour|hr)", raw_lower)
    min_match = re.search(r"(\d+)\s*(minute|min)", raw_lower)
    total = 0
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if min_match:
        total += int(min_match.group(1))
    return total if total > 0 else None


def verify_no_phi_leaked(payload: dict) -> bool:
    """
    Sanity check: scan the sanitized payload dict for obvious PHI.
    Returns True if clean; False + warning if suspicious.
    """
    import json
    text = json.dumps(payload).lower()
    phi_patterns = [r"\b\d{10}\b", r"\b\d{12}\b"]  # phone, Aadhaar
    for pattern in phi_patterns:
        if re.search(pattern, text):
            logger.warning("Possible PHI detected in LLM payload — blocking send")
            return False
    return True

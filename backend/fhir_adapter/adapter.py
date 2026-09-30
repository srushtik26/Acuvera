"""
FHIR R4 Adapter — maps Acuvera internal models to/from FHIR R4 resources.
Endpoints: Patient, Encounter, Observation, Task.
See SPEC.md §5 FHIR section.
"""
import logging
from django.utils import timezone

logger = logging.getLogger("acuvera.fhir.adapter")


# ─── FHIR → Internal model converters ──────────────────────────────────────

def fhir_patient_to_internal(resource: dict) -> dict:
    """Convert FHIR R4 Patient resource to Acuvera patient dict."""
    name_entry = resource.get("name", [{}])[0]
    family = name_entry.get("family", "")
    given = " ".join(name_entry.get("given", []))
    full_name = f"{given} {family}".strip() or None

    gender_map = {"male": "male", "female": "female", "other": "other", "unknown": "unknown"}
    fhir_gender = resource.get("gender", "unknown")

    birth_date = resource.get("birthDate")
    age = None
    if birth_date:
        from datetime import date
        try:
            bd = date.fromisoformat(birth_date)
            today = date.today()
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except ValueError:
            pass

    identifier = resource.get("identifier", [{}])
    external_id = identifier[0].get("value") if identifier else None

    phone = None
    for telecom in resource.get("telecom", []):
        if telecom.get("system") == "phone":
            phone = telecom.get("value")
            break

    return {
        "name": full_name,
        "gender": gender_map.get(fhir_gender, "unknown"),
        "dob": birth_date,
        "age": age,
        "external_id": external_id,
        "contact_phone": phone,
    }


def internal_patient_to_fhir(patient) -> dict:
    """Convert Acuvera Patient model to FHIR R4 Patient resource."""
    resource = {
        "resourceType": "Patient",
        "id": str(patient.id),
        "meta": {"lastUpdated": patient.created_at.isoformat()},
        "identifier": [{"system": "urn:acuvera:patient", "value": str(patient.id)}],
        "gender": patient.gender or "unknown",
    }
    if patient.name:
        parts = patient.name.split(" ", 1)
        resource["name"] = [{"use": "official", "family": parts[-1], "given": [parts[0]]}]
    if patient.dob:
        resource["birthDate"] = patient.dob.isoformat()
    if patient.contact_phone:
        resource["telecom"] = [{"system": "phone", "value": patient.contact_phone}]
    if patient.external_id:
        resource["identifier"].append({"system": "urn:hospital:mrn", "value": patient.external_id})
    return resource


def fhir_encounter_to_internal(resource: dict) -> dict:
    """Convert FHIR R4 Encounter to Acuvera encounter dict."""
    status_map = {
        "planned": "waiting", "arrived": "waiting", "triaged": "waiting",
        "in-progress": "in_progress", "finished": "completed", "cancelled": "cancelled",
    }
    fhir_status = resource.get("status", "arrived")
    patient_ref = resource.get("subject", {}).get("reference", "")
    dept_ref = resource.get("serviceProvider", {}).get("reference", "")
    patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
    dept_id = dept_ref.split("/")[-1] if "/" in dept_ref else dept_ref

    return {
        "patient_id": patient_id,
        "department_id": dept_id,
        "status": status_map.get(fhir_status, "waiting"),
        "triage_stage": "rapid",
    }


def internal_encounter_to_fhir(encounter) -> dict:
    """Convert Acuvera Encounter to FHIR R4 Encounter."""
    status_map = {
        "waiting": "triaged", "assigned": "triaged", "in_progress": "in-progress",
        "completed": "finished", "escalated": "in-progress", "cancelled": "cancelled",
    }
    priority_map = {
        "low": "routine", "moderate": "urgent", "high": "urgent", "critical": "asap",
    }
    return {
        "resourceType": "Encounter",
        "id": str(encounter.id),
        "status": status_map.get(encounter.status, "triaged"),
        "priority": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActPriority",
                                  "code": priority_map.get(encounter.priority, "urgent")}]},
        "subject": {"reference": f"Patient/{encounter.patient_id}"},
        "serviceProvider": {"reference": f"Organization/{encounter.department_id}"},
        "period": {"start": encounter.created_at.isoformat()},
        "meta": {"lastUpdated": encounter.updated_at.isoformat()},
    }


def fhir_observation_to_triagedata(resource: dict) -> dict:
    """Convert FHIR R4 Observation to vitals_json fields."""
    vitals = {}
    # LOINC code mapping for common vitals
    loinc_map = {
        "8867-4": "hr",     # Heart rate
        "59408-5": "spo2",  # Oxygen saturation
        "8480-6": "bp_systolic",
        "8462-4": "bp_diastolic",
        "8310-5": "temp",   # Body temperature
        "9279-1": "rr",     # Respiratory rate
        "9268-4": "gcs",    # GCS total
    }
    codings = resource.get("code", {}).get("coding", [])
    for coding in codings:
        loinc = coding.get("code", "")
        key = loinc_map.get(loinc)
        if key:
            value_quantity = resource.get("valueQuantity", {})
            if "value" in value_quantity:
                vitals[key] = value_quantity["value"]
    encounter_ref = resource.get("encounter", {}).get("reference", "")
    encounter_id = encounter_ref.split("/")[-1] if "/" in encounter_ref else None
    return {"encounter_id": encounter_id, "vitals": vitals}


def internal_triagedata_to_fhir_observation(triage_data, encounter) -> list:
    """
    Convert Acuvera TriageData vitals to a list of FHIR R4 Observations (one per vital).
    """
    vitals = triage_data.vitals_json or {}
    observations = []
    loinc_map = {
        "hr": ("8867-4", "Heart rate", "/min"),
        "spo2": ("59408-5", "Oxygen saturation", "%"),
        "bp_systolic": ("8480-6", "Systolic blood pressure", "mmHg"),
        "bp_diastolic": ("8462-4", "Diastolic blood pressure", "mmHg"),
        "temp": ("8310-5", "Body temperature", "[degF]"),
        "rr": ("9279-1", "Respiratory rate", "/min"),
        "gcs": ("9268-4", "Glasgow coma scale total", "{score}"),
    }
    for field, (loinc, display, unit) in loinc_map.items():
        value = vitals.get(field)
        if value is not None:
            observations.append({
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": display}]},
                "subject": {"reference": f"Patient/{encounter.patient_id}"},
                "encounter": {"reference": f"Encounter/{encounter.id}"},
                "valueQuantity": {"value": value, "unit": unit},
                "effectiveDateTime": triage_data.created_at.isoformat(),
            })
    return observations

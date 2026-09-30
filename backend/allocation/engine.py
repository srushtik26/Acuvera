"""
Acuvera Allocation Engine — deterministic, fair, starvation-aware.
See SPEC.md §6.B for the exact algorithm specification.
"""
import logging
from django.db import transaction
from django.utils import timezone

from core.audit import log_audit, model_snapshot

logger = logging.getLogger("acuvera.allocation.engine")

PRIORITY_WORKLOAD_WEIGHTS = {
    "critical": 3,
    "high": 2,
    "moderate": 1,
    "low": 0.5,
}


def compute_doctor_workload(doctor_id: str) -> float:
    """
    Workload = critical*3 + high*2 + moderate*1 + low*0.5
    Counts only ACTIVE cases: assigned, in_progress, escalated.
    Explicitly excludes completed, cancelled, and waiting encounters.
    """
    from core.models import Encounter
    active = Encounter.objects.filter(
        assigned_doctor_id=doctor_id,
        status__in=("assigned", "in_progress", "escalated"),
        is_deleted=False,
    ).values_list("priority", flat=True)

    workload = sum(PRIORITY_WORKLOAD_WEIGHTS.get(p, 0.5) for p in active)
    return workload


def get_candidate_doctors(department_id: str, max_cases: int = 6) -> list:
    """
    Return ALL active doctors in the department, sorted by:
    1. Availability (available > in_procedure > others)
    2. Workload (ascending)
    3. Last assigned (ascending, for fairness)

    No hard filter on availability_state — the nurse should always be able
    to assign, even if all doctors are busy. The availability state is shown
    so the nurse can make an informed decision.
    """
    from core.models import User
    now = timezone.now()

    # Include ALL active doctors in the department, regardless of state
    doctors = User.objects.filter(
        department_id=department_id,
        role="doctor",
        is_active=True,
    ).select_related("department")

    AVAIL_ORDER = {
        "available": 0,
        "in_procedure": 1,
        "emergency": 2,
        "unavailable": 3,
        "off_shift": 4,
    }

    candidates = []
    for doc in doctors:
        # Skip if explicitly off-shift and shift times are configured
        if doc.shift_start and doc.shift_end:
            if not (doc.shift_start <= now <= doc.shift_end):
                continue

        workload = compute_doctor_workload(str(doc.id))
        candidates.append({
            "doctor": doc,
            "workload": workload,
            "avail_rank": AVAIL_ORDER.get(doc.availability_state, 2),
            "last_assigned_at": doc.last_assigned_at or timezone.datetime.min.replace(tzinfo=timezone.utc),
        })

    # Sort: available first, then least loaded, then least recently assigned
    candidates.sort(key=lambda c: (c["avail_rank"], c["workload"], c["last_assigned_at"]))
    return candidates



def try_assign_doctor(encounter_id: str, doctor_id: str, reason: str = "auto_assign",
                      requested_by=None, request=None,
                      floor=None, room_number=None, bed_number=None) -> bool:
    """
    Attempt to assign a doctor to an encounter.
    Uses SELECT FOR UPDATE to prevent race conditions.
    Returns True if successful, False if encounter already assigned.
    """
    from core.models import Encounter, User, AllocationLog
    try:
        with transaction.atomic():
            enc = Encounter.objects.select_for_update().get(pk=encounter_id, is_deleted=False)
            doctor = User.objects.get(pk=doctor_id, is_active=True)

            if enc.assigned_doctor_id and enc.status not in ("waiting",):
                if reason not in ("doctor_referral", "manual_confirm", "manual_nurse_reassignment"):
                    logger.info("Encounter %s already assigned to %s — skipping", encounter_id, enc.assigned_doctor_id)
                    return False

            pre = model_snapshot(enc)
            old_doctor_id = enc.assigned_doctor_id

            enc.assigned_doctor = doctor
            enc.status = "assigned"
            if floor is not None:
                enc.floor = floor
            if room_number is not None:
                enc.room_number = room_number
            if bed_number is not None:
                enc.bed_number = bed_number
            enc.version += 1
            enc.save()

            doctor.last_assigned_at = timezone.now()
            doctor.save(update_fields=["last_assigned_at"])

            AllocationLog.objects.create(
                encounter=enc,
                from_doctor_id=old_doctor_id,
                to_doctor=doctor,
                reason=reason,
                accepted=True,
            )
            log_audit("allocation.assign", "encounter", enc.id, requested_by, pre, model_snapshot(enc), request,
                      metadata={"doctor_id": str(doctor_id), "reason": reason})

            logger.info("Encounter %s assigned to doctor %s (workload: %.1f)",
                        encounter_id, doctor_id, compute_doctor_workload(str(doctor_id)))
            return True

    except (Encounter.DoesNotExist, User.DoesNotExist) as e:
        logger.warning("Assignment failed: %s", e)
        return False


def auto_allocate(encounter_id: str, request=None) -> dict:
    """
    Auto-allocate the best available doctor for an encounter.
    Tries candidates in order; returns the assigned doctor or escalates.
    """
    from core.models import Encounter, HospitalConfig
    from django.conf import settings

    try:
        enc = Encounter.objects.select_related("department").get(pk=encounter_id, is_deleted=False)
    except Encounter.DoesNotExist:
        return {"success": False, "error": "Encounter not found"}

    config = HospitalConfig.objects.first()
    max_cases = config.max_active_cases_per_doctor if config else settings.FEATURE_FLAGS_DEFAULT.get("max_cases", 6)

    candidates = get_candidate_doctors(str(enc.department_id), max_cases=max_cases)
    if not candidates:
        logger.warning("No available doctors for encounter %s in dept %s", encounter_id, enc.department_id)
        return {"success": False, "error": "No available doctors", "escalated": False}

    for candidate in candidates:
        doctor = candidate["doctor"]
        success = try_assign_doctor(encounter_id, str(doctor.id), reason="auto_assign", request=request)
        if success:
            return {
                "success": True,
                "doctor_id": str(doctor.id),
                "doctor_name": doctor.full_name,
                "workload": candidate["workload"],
            }

    return {"success": False, "error": "All candidates failed assignment"}


def suggest_doctor(encounter_id: str) -> dict:
    """
    Return the top-ranked candidate doctor without assigning.
    Used by nurse UI to display suggestion.
    """
    from core.models import Encounter, HospitalConfig
    from django.conf import settings

    try:
        enc = Encounter.objects.select_related("department").get(pk=encounter_id, is_deleted=False)
    except Encounter.DoesNotExist:
        return {"success": False, "error": "Encounter not found"}

    config = HospitalConfig.objects.first()
    max_cases = config.max_active_cases_per_doctor if config else 6

    candidates = get_candidate_doctors(str(enc.department_id), max_cases=max_cases)
    if not candidates:
        return {"success": False, "error": "No available doctors"}

    top = candidates[0]
    return {
        "success": True,
        "doctor_id": str(top["doctor"].id),
        "doctor_name": top["doctor"].full_name,
        "workload_score": top["workload"],
        "availability_state": top["doctor"].availability_state,
    }


def handle_rejection(encounter_id: str, doctor_id: str, rejection_reason: str,
                     requested_by=None, request=None) -> dict:
    """
    Record a doctor rejection and attempt allocation to next candidate.
    After MAX_DOCTOR_REJECTIONS, escalate to dept head.
    """
    from core.models import Encounter, User, AllocationLog
    from django.conf import settings

    try:
        with transaction.atomic():
            enc = Encounter.objects.select_for_update().get(pk=encounter_id, is_deleted=False)
            doctor = User.objects.get(pk=doctor_id)

            AllocationLog.objects.create(
                encounter=enc,
                from_doctor=doctor,
                to_doctor=None,
                reason="doctor_rejection",
                accepted=False,
                rejection_reason=rejection_reason,
            )

            enc.rejection_count += 1
            enc.assigned_doctor = None
            enc.status = "waiting"
            enc.version += 1
            enc.save()

            log_audit("allocation.reject", "encounter", enc.id, requested_by, None, None, request,
                      metadata={"doctor_id": str(doctor_id), "reason": rejection_reason,
                                "rejection_count": enc.rejection_count})

        max_rejections = getattr(settings, "MAX_DOCTOR_REJECTIONS", 3)
        if enc.rejection_count >= max_rejections:
            logger.warning(
                "Encounter %s reached max rejections (%d) — escalating to dept head",
                encounter_id, enc.rejection_count
            )
            from escalation.engine import trigger_escalation
            trigger_escalation(
                encounter_id=encounter_id,
                escalation_type="manual_escalation",
                triggered_by=None,
                reason=f"Auto-escalated after {enc.rejection_count} doctor rejections",
                request=request,
            )
            return {"success": True, "escalated": True, "rejection_count": enc.rejection_count}

        # Return to waiting state, alert nurse UI
        return {"success": True, "escalated": False,
                "rejection_count": enc.rejection_count}

    except (Encounter.DoesNotExist, User.DoesNotExist) as e:
        return {"success": False, "error": str(e)}

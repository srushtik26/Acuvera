"""
Acuvera Escalation Engine.
See SPEC.md §6.C for the exact algorithm specification.
"""
import logging
from django.db import transaction
from django.utils import timezone

from core.audit import log_audit, model_snapshot

logger = logging.getLogger("acuvera.escalation.engine")

SLA_DEFAULTS = {
    "code_blue": 120,       # 2 minutes
    "trauma_override": 300,  # 5 minutes
    "manual_escalation": 900,  # 15 minutes
}

ICU_BEDS = [
    "ICU-A1", "ICU-A2", "ICU-A3", "ICU-A4",
    "ICU-B1", "ICU-B2", "ICU-B3", "ICU-B4",
]

def assign_icu_bed() -> str:
    """Round-robin ICU bed assignment based on current active code blue count."""
    from core.models import EscalationEvent
    count = EscalationEvent.objects.filter(type="code_blue", acknowledged_at__isnull=True).count()
    return ICU_BEDS[count % len(ICU_BEDS)]


def trigger_escalation(
    encounter_id: str,
    escalation_type: str,
    triggered_by=None,
    reason: str = "",
    request=None,
) -> dict:
    """
    Trigger an escalation event for an encounter.
    1. Sets priority to critical and status to escalated.
    2. Creates EscalationEvent record.
    3. Logs audit trail.
    4. Marks encounter for SLA timer.
    """
    from core.models import Encounter, EscalationEvent, HospitalConfig

    valid_types = ("code_blue", "trauma_override", "manual_escalation")
    if escalation_type not in valid_types:
        return {"success": False, "error": f"Invalid escalation type. Must be one of {valid_types}"}

    try:
        with transaction.atomic():
            enc = Encounter.objects.select_for_update().get(pk=encounter_id, is_deleted=False)
            pre = model_snapshot(enc)

            enc.priority = "critical"
            enc.status = "escalated"
            enc.version += 1
            if escalation_type == "code_blue":
                enc.code_blue_active = True
                enc.code_blue_acknowledged = False
            enc.save()

            # Auto-assign ICU bed for code blue events
            icu_bed = assign_icu_bed() if escalation_type == "code_blue" else None

            event = EscalationEvent.objects.create(
                encounter=enc,
                type=escalation_type,
                triggered_by=triggered_by,
            )

            log_audit(
                f"escalation.{escalation_type}",
                "encounter",
                enc.id,
                triggered_by,
                pre,
                model_snapshot(enc),
                request,
                metadata={"escalation_event_id": str(event.id), "reason": reason},
            )

            logger.warning(
                "ESCALATION triggered: encounter=%s type=%s triggered_by=%s",
                encounter_id, escalation_type, triggered_by
            )

        patient_name = enc.patient.name if enc.patient else "Unknown"
        return {
            "success": True,
            "escalation_event_id": str(event.id),
            "encounter_id": str(enc.id),
            "patient_name": patient_name,
            "type": escalation_type,
            "icu_bed": icu_bed,
            "timestamp": event.timestamp.isoformat(),
        }

    except Encounter.DoesNotExist:
        return {"success": False, "error": "Encounter not found"}


def acknowledge_escalation(event_id: str, acknowledging_nurse=None, request=None) -> dict:
    """
    Nurse clicks 'Acknowledge' on a Code Blue — records response_time for audit.
    The encounter stays escalated; the doctor on the case continues managing it.
    """
    from core.models import EscalationEvent, HospitalConfig
    try:
        event = EscalationEvent.objects.get(pk=event_id)
        if event.acknowledged_at:
            return {"success": False, "error": "Already acknowledged"}

        now = timezone.now()
        response_time = int((now - event.timestamp).total_seconds())

        # Check SLA
        config = HospitalConfig.objects.first()
        sla_map = {
            "code_blue": config.sla_code_blue_seconds if config else SLA_DEFAULTS["code_blue"],
            "trauma_override": config.sla_trauma_seconds if config else SLA_DEFAULTS["trauma_override"],
            "manual_escalation": config.sla_manual_seconds if config else SLA_DEFAULTS["manual_escalation"],
        }
        sla_threshold = sla_map.get(event.type, SLA_DEFAULTS.get(event.type, 900))
        sla_breached = response_time > sla_threshold

        event.response_time = response_time
        event.acknowledged_by = acknowledging_nurse
        event.acknowledged_at = now
        event.sla_breached = sla_breached
        event.save()

        # Persist Code Blue acknowledgement on Encounter so it survives page reload
        if event.type == "code_blue":
            from core.models import Encounter
            try:
                enc = event.encounter
                enc.code_blue_acknowledged = True
                enc.code_blue_acknowledged_by = acknowledging_nurse
                enc.code_blue_acknowledged_at = now
                enc.save(update_fields=[
                    "code_blue_acknowledged",
                    "code_blue_acknowledged_by",
                    "code_blue_acknowledged_at",
                ])
            except Exception as upd_err:
                logger.warning("Could not update Code Blue ack on encounter: %s", upd_err)

        if sla_breached:
            logger.error(
                "SLA BREACHED: escalation=%s type=%s response_time=%ds threshold=%ds",
                event_id, event.type, response_time, sla_threshold
            )

        log_audit(
            "escalation.acknowledge", "escalation_event", event.id,
            acknowledging_nurse, None, None, request,
            metadata={"response_time_s": response_time, "sla_breached": sla_breached},
        )

        return {
            "success": True,
            "response_time_seconds": response_time,
            "sla_breached": sla_breached,
            "sla_threshold_seconds": sla_threshold,
            "acknowledged_at": now.isoformat(),
        }

    except EscalationEvent.DoesNotExist:
        return {"success": False, "error": "Escalation event not found"}


def check_sla_breaches() -> list:
    """
    Called by the scheduler every 30 seconds.
    Returns list of escalation events that have breached SLA and are not yet acknowledged.
    """
    from core.models import EscalationEvent, HospitalConfig

    config = HospitalConfig.objects.first()
    now = timezone.now()
    breached = []

    unacknowledged = EscalationEvent.objects.filter(acknowledged_at__isnull=True)
    for event in unacknowledged:
        sla_map = {
            "code_blue": config.sla_code_blue_seconds if config else SLA_DEFAULTS["code_blue"],
            "trauma_override": config.sla_trauma_seconds if config else SLA_DEFAULTS["trauma_override"],
            "manual_escalation": config.sla_manual_seconds if config else SLA_DEFAULTS["manual_escalation"],
        }
        threshold = sla_map.get(event.type, 900)
        elapsed = (now - event.timestamp).total_seconds()
        if elapsed > threshold and not event.sla_breached:
            event.sla_breached = True
            event.save(update_fields=["sla_breached"])
            breached.append({
                "event_id": str(event.id),
                "encounter_id": str(event.encounter_id),
                "type": event.type,
                "elapsed_seconds": int(elapsed),
                "sla_threshold": threshold,
            })
            logger.error("SLA breach detected: %s", breached[-1])

    return breached

"""
APScheduler in-process background jobs.
No Celery, no Redis — all jobs run inside the Django/gunicorn process.
"""
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

logger = logging.getLogger("acuvera.scheduler")

_scheduler = None
_lock = threading.Lock()


def _on_job_error(event):
    logger.error("Scheduled job %s raised an exception: %s", event.job_id, event.exception)


def start_scheduler():
    """
    Start the APScheduler background scheduler.
    Called once from SchedulerConfig.ready().
    Thread-safe using a global lock.
    """
    global _scheduler
    with _lock:
        if _scheduler and _scheduler.running:
            return

        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)

        # Job 1: Starvation detection — every 2 minutes
        _scheduler.add_job(
            _starvation_scan,
            trigger="interval",
            minutes=2,
            id="starvation_scan",
            replace_existing=True,
            max_instances=1,
        )

        # Job 2: SLA breach check — every 30 seconds
        _scheduler.add_job(
            _sla_breach_check,
            trigger="interval",
            seconds=30,
            id="sla_breach_check",
            replace_existing=True,
            max_instances=1,
        )

        # Job 3: Daily analytics snapshot — every day at midnight UTC
        _scheduler.add_job(
            _daily_snapshot,
            trigger="cron",
            hour=0,
            minute=0,
            id="daily_snapshot",
            replace_existing=True,
            max_instances=1,
        )

        # Job 4: Off-shift doctor reassignment — every 5 minutes
        _scheduler.add_job(
            _offshift_reassignment,
            trigger="interval",
            minutes=5,
            id="offshift_reassignment",
            replace_existing=True,
            max_instances=1,
        )

        _scheduler.start()
        logger.info("APScheduler started with %d jobs", len(_scheduler.get_jobs()))


def get_scheduler_status() -> str:
    if _scheduler and _scheduler.running:
        jobs = _scheduler.get_jobs()
        return f"running ({len(jobs)} jobs)"
    return "stopped"


# ─── Job implementations ───────────────────────────────────────────────────────

def _starvation_scan():
    """
    Detect encounters that have been waiting longer than the department threshold.
    Sets a DB flag / creates notification record for nurse UI.
    """
    import django
    try:
        from core.models import Encounter, Department
        from django.utils import timezone

        now = timezone.now()
        waiting_encounters = Encounter.objects.filter(
            status__in=("waiting", "assigned"),
            is_deleted=False,
        ).select_related("department")

        starving = []
        for enc in waiting_encounters:
            threshold_min = enc.department.starvation_threshold_minutes
            wait_min = (now - enc.created_at).total_seconds() / 60.0
            if wait_min > threshold_min:
                starving.append({
                    "encounter_id": str(enc.id),
                    "department_id": str(enc.department_id),
                    "wait_minutes": round(wait_min, 1),
                    "threshold_minutes": threshold_min,
                    "priority": enc.priority,
                })

        if starving:
            logger.warning("Starvation scan: %d starving encounters detected", len(starving))
            from core.audit import log_audit
            for item in starving:
                log_audit(
                    "system.starvation_detected",
                    "encounter",
                    item["encounter_id"],
                    user=None,
                    metadata=item,
                )
    except Exception as e:
        logger.error("Starvation scan job failed: %s", e, exc_info=True)


def _sla_breach_check():
    """Check for unacknowledged escalations that have breached SLA."""
    try:
        from escalation.engine import check_sla_breaches
        breaches = check_sla_breaches()
        if breaches:
            logger.error("SLA breach job: %d breaches found", len(breaches))
    except Exception as e:
        logger.error("SLA breach check job failed: %s", e, exc_info=True)


def _daily_snapshot():
    """Aggregate daily AnalyticsSnapshot for all departments."""
    try:
        from analytics.engine import take_daily_snapshot
        count = take_daily_snapshot()
        logger.info("Daily snapshot job completed: %d departments", count)
    except Exception as e:
        logger.error("Daily snapshot job failed: %s", e, exc_info=True)


def _offshift_reassignment():
    """
    Detect doctors whose shift has ended but still have assigned encounters.
    Attempts re-allocation or marks encounters for nurse attention.
    """
    try:
        from core.models import User, Encounter
        from django.utils import timezone
        from allocation.engine import auto_allocate

        now = timezone.now()
        # Doctors whose shift ended but are still 'available'
        off_shift_doctors = User.objects.filter(
            role="doctor",
            is_active=True,
            shift_end__lt=now,
            availability_state="available",
        )

        for doctor in off_shift_doctors:
            # Mark as off_shift
            doctor.availability_state = "off_shift"
            doctor.save(update_fields=["availability_state", "updated_at"])

            # Reassign their waiting/assigned encounters
            their_encounters = Encounter.objects.filter(
                assigned_doctor=doctor,
                status__in=("waiting", "assigned"),
                is_deleted=False,
            )
            for enc in their_encounters:
                logger.info("Off-shift reassignment: encounter %s from doctor %s", enc.id, doctor.id)
                auto_allocate(str(enc.id))

    except Exception as e:
        logger.error("Off-shift reassignment job failed: %s", e, exc_info=True)

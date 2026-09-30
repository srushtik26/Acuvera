"""
Analytics engine — operational metrics, forecasting, financial impact.
See SPEC.md §8.
"""
import logging
import math
from datetime import date, timedelta
from django.db import connection
from django.utils import timezone

logger = logging.getLogger("acuvera.analytics.engine")


def get_operational_overview(department_id: str = None) -> dict:
    """
    Real-time operational metrics for admin dashboard.
    """
    from core.models import Encounter, User, Department

    qs = Encounter.objects.filter(is_deleted=False)
    if department_id:
        qs = qs.filter(department_id=department_id)

    active = qs.filter(status__in=("waiting", "assigned", "in_progress"))
    active_count = active.count()

    # Priority distribution
    priority_dist = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    for enc in active.values("priority"):
        priority_dist[enc["priority"]] = priority_dist.get(enc["priority"], 0) + 1

    # Average wait time (seconds) for waiting+assigned
    waiting = active.filter(status__in=("waiting", "assigned"))
    now = timezone.now()
    wait_times = [(now - e.created_at).total_seconds() for e in waiting]
    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0

    # Starvation detection
    from core.models import HospitalConfig, Department
    config = HospitalConfig.objects.first()
    dept_configs = {}
    if department_id:
        try:
            dept = Department.objects.get(pk=department_id)
            dept_configs[department_id] = dept
        except Department.DoesNotExist:
            pass
    else:
        for dept in Department.objects.filter(is_active=True):
            dept_configs[str(dept.id)] = dept

    starvation_count = 0
    for enc in waiting:
        dept = dept_configs.get(str(enc.department_id))
        threshold_min = dept.starvation_threshold_minutes if dept else 30
        wait_min = (now - enc.created_at).total_seconds() / 60
        if wait_min > threshold_min:
            starvation_count += 1

    # Overloaded doctors (workload > 8)
    from allocation.engine import compute_doctor_workload
    doctors = User.objects.filter(role="doctor", is_active=True)
    if department_id:
        doctors = doctors.filter(department_id=department_id)
    overloaded = sum(1 for d in doctors if compute_doctor_workload(str(d.id)) > 8)

    return {
        "active_patients": active_count,
        "priority_distribution": priority_dist,
        "avg_wait_time_seconds": round(avg_wait),
        "starvation_count": starvation_count,
        "overloaded_doctors": overloaded,
        "total_doctors": doctors.count(),
    }


def get_doctor_utilization(doctor_id: str, shift_hours: float = 8.0) -> dict:
    """
    Calculate utilization % for a doctor during their current/last shift.
    """
    from core.models import User, Encounter
    from allocation.engine import compute_doctor_workload

    try:
        doctor = User.objects.get(pk=doctor_id)
    except User.DoesNotExist:
        return {}

    workload = compute_doctor_workload(str(doctor.id))
    # Rough utilization: ratio of workload to shift capacity
    # Each "case" assumed avg 30 min handling time
    avg_handle_minutes = 30
    max_capacity = (shift_hours * 60) / avg_handle_minutes
    utilization_pct = min(100, round((workload / max_capacity) * 100)) if max_capacity > 0 else 0

    return {
        "doctor_id": str(doctor.id),
        "doctor_name": doctor.full_name,
        "current_workload_score": workload,
        "availability_state": doctor.availability_state,
        "utilization_pct": utilization_pct,
        "shift_hours": shift_hours,
    }


def compute_peak_hour_forecast(department_id: str, days_ahead: int = 7) -> dict:
    """
    Peak hour forecast using hourly exponential smoothing over 90-day history.
    Returns hourly traffic predictions for the next `days_ahead` days.
    """
    from core.models import Encounter
    from django.db.models import Count
    from django.db.models.functions import ExtractHour, ExtractWeekDay

    cutoff = timezone.now() - timedelta(days=90)
    qs = Encounter.objects.filter(
        department_id=department_id,
        created_at__gte=cutoff,
        is_deleted=False,
    ).annotate(
        hour=ExtractHour("created_at"),
        weekday=ExtractWeekDay("created_at"),
    ).values("hour", "weekday").annotate(count=Count("id"))

    # Build hour → avg count map
    hourly_counts = {}
    for row in qs:
        h = row["hour"]
        hourly_counts.setdefault(h, []).append(row["count"])

    # Exponential smoothing (alpha = 0.3)
    alpha = 0.3
    hourly_forecast = {}
    for hour in range(24):
        counts = hourly_counts.get(hour, [0])
        smoothed = counts[0]
        for c in counts[1:]:
            smoothed = alpha * c + (1 - alpha) * smoothed
        variance = sum((c - smoothed) ** 2 for c in counts) / len(counts) if counts else 0
        std_dev = math.sqrt(variance)
        hourly_forecast[hour] = {
            "expected": round(smoothed, 1),
            "low": max(0, round(smoothed - std_dev, 1)),
            "high": round(smoothed + std_dev, 1),
        }

    peak_hour = max(hourly_forecast, key=lambda h: hourly_forecast[h]["expected"])
    return {
        "forecast_days": days_ahead,
        "hourly_forecast": hourly_forecast,
        "peak_hour": peak_hour,
        "peak_expected_count": hourly_forecast[peak_hour]["expected"],
    }


def compute_overload_probability(department_id: str, capacity: int = 10) -> dict:
    """
    Poisson-based overload probability: P(arrivals > capacity) for next hour.
    """
    import scipy.stats as stats

    from core.models import Encounter
    from django.db.models import Count
    from django.db.models.functions import TruncHour

    cutoff = timezone.now() - timedelta(days=30)
    hourly = (
        Encounter.objects.filter(department_id=department_id, created_at__gte=cutoff)
        .annotate(hour=TruncHour("created_at"))
        .values("hour")
        .annotate(count=Count("id"))
    )
    counts = [row["count"] for row in hourly]
    if not counts:
        return {"probability": 0.0, "lambda": 0}

    lambda_ = sum(counts) / len(counts)
    # P(X > capacity) = 1 - CDF(capacity)
    try:
        prob = 1 - stats.poisson.cdf(capacity, lambda_)
    except Exception:
        prob = 0.0

    return {
        "lambda_per_hour": round(lambda_, 2),
        "capacity": capacity,
        "overload_probability": round(prob, 4),
        "overload_pct": round(prob * 100, 1),
    }


def compute_staffing_suggestion(expected_arrivals_per_hour: float, avg_handling_minutes: float,
                                 target_avg_wait_minutes: float) -> dict:
    """
    Staffing formula from SPEC:
    recommended_doctors = ceil(expected_arrivals_per_hour * avg_handling_hours / desired_throughput)
    """
    avg_handling_hours = avg_handling_minutes / 60.0
    # Desired throughput = 1 patient / target_wait_hours per doctor slot
    desired_throughput = 1 / (target_avg_wait_minutes / 60.0) if target_avg_wait_minutes > 0 else 1
    recommended = math.ceil(expected_arrivals_per_hour * avg_handling_hours / (1 / desired_throughput))
    return {
        "expected_arrivals_per_hour": expected_arrivals_per_hour,
        "avg_handling_minutes": avg_handling_minutes,
        "target_avg_wait_minutes": target_avg_wait_minutes,
        "recommended_doctors": max(1, recommended),
    }


def compute_financial_impact(department_id: str, period_days: int = 30) -> dict:
    """
    Financial impact calculation.
    Compares current throughput to previous period.
    """
    from core.models import Encounter, HospitalConfig

    config = HospitalConfig.objects.first()
    avg_revenue = float(config.avg_revenue_per_patient) if config else 500.0  # ₹500 default

    now = timezone.now()
    current_start = now - timedelta(days=period_days)
    previous_start = now - timedelta(days=period_days * 2)

    current_throughput = Encounter.objects.filter(
        department_id=department_id,
        status="completed",
        created_at__gte=current_start,
        is_deleted=False,
    ).count()

    previous_throughput = Encounter.objects.filter(
        department_id=department_id,
        status="completed",
        created_at__gte=previous_start,
        created_at__lt=current_start,
        is_deleted=False,
    ).count()

    delta = current_throughput - previous_throughput
    impact = delta * avg_revenue

    return {
        "period_days": period_days,
        "current_throughput": current_throughput,
        "previous_throughput": previous_throughput,
        "throughput_delta": delta,
        "avg_revenue_per_patient": avg_revenue,
        "estimated_revenue_impact": round(impact, 2),
        "scenarios": {
            "conservative": round((delta * 0.9) * avg_revenue, 2),
            "expected": round(impact, 2),
            "optimistic": round((delta * 1.1) * avg_revenue, 2),
        },
    }


def take_daily_snapshot(target_date: date = None) -> int:
    """
    Aggregate and persist daily AnalyticsSnapshot for all active departments.
    Called by APScheduler job. Returns number of snapshots created/updated.
    """
    from core.models import Department, Encounter, AnalyticsSnapshot
    from allocation.engine import compute_doctor_workload

    target_date = target_date or timezone.now().date()
    count = 0

    for dept in Department.objects.filter(is_active=True):
        dept_id = str(dept.id)
        qs = Encounter.objects.filter(
            department_id=dept_id,
            created_at__date=target_date,
            is_deleted=False,
        )
        completed = qs.filter(status="completed")
        throughput = completed.count()

        waits = []
        for enc in qs.filter(status="completed"):
            waits.append((enc.updated_at - enc.created_at).total_seconds())
        avg_wait = sum(waits) / len(waits) if waits else 0

        starvation_count = sum(
            1 for enc in qs.filter(status__in=("waiting", "assigned"))
            if (timezone.now() - enc.created_at).total_seconds() / 60 > dept.starvation_threshold_minutes
        )

        escalation_count = Encounter.objects.filter(
            department_id=dept_id,
            status="escalated",
            created_at__date=target_date,
        ).count()

        AnalyticsSnapshot.objects.update_or_create(
            date=target_date,
            department=dept,
            defaults={
                "avg_wait_time": avg_wait,
                "starvation_count": starvation_count,
                "escalation_count": escalation_count,
                "throughput": throughput,
            },
        )
        count += 1

    logger.info("Daily snapshot taken for %d departments on %s", count, target_date)
    return count

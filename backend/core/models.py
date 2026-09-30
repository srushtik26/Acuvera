"""
Acuvera core data models — canonical source of truth.
All tables use UUID PKs, soft deletes, UTC timestamps, and version-based optimistic locking.
psycopg3 compatible → Supabase-ready.
"""
import uuid
from django.db import models


class Department(models.Model):
    """Hospital department (e.g., general, cardiac, trauma)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    starvation_threshold_minutes = models.IntegerField(default=30)
    # E.g.: {"SpO2_low": 20, "SpO2_low_threshold": 90, "HR_high": 15, "HR_high_threshold": 120, ...}
    priority_weight_config = models.JSONField(default=dict)
    profile_type = models.CharField(max_length=50, default="general")  # cardiac, trauma, pediatrics, etc.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "departments"

    def __str__(self):
        return f"{self.name} ({self.profile_type})"


class User(models.Model):
    """Platform user (nurse, doctor, admin, dept_head)."""
    ROLE_CHOICES = [
        ("nurse", "Nurse"),
        ("doctor", "Doctor"),
        ("admin", "Admin"),
        ("dept_head", "Department Head"),
    ]
    AVAILABILITY_CHOICES = [
        ("available", "Available"),
        ("in_procedure", "In Procedure"),
        ("off_shift", "Off Shift"),
        ("emergency", "Emergency"),
        ("unavailable", "Unavailable"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clerk_user_id = models.TextField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    password_hash = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    is_active = models.BooleanField(default=True)
    availability_state = models.CharField(
        max_length=20, choices=AVAILABILITY_CHOICES, default="available"
    )
    shift_start = models.DateTimeField(null=True, blank=True)
    shift_end = models.DateTimeField(null=True, blank=True)
    last_assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    @property
    def is_on_shift(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.shift_start or not self.shift_end:
            return True  # No shift configured → always on shift
        return self.shift_start <= now <= self.shift_end


class Patient(models.Model):
    """Patient record. Name and identifiers are optional to support anonymized mode."""
    GENDER_CHOICES = [("male", "Male"), ("female", "Female"), ("other", "Other"), ("unknown", "Unknown")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.TextField(null=True, blank=True)  # MRN from EHR
    name = models.TextField(null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="unknown")
    contact_phone = models.TextField(null=True, blank=True)
    is_anonymized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patients"

    def __str__(self):
        return f"Patient {self.external_id or self.id}"


class Encounter(models.Model):
    """Core clinical encounter record — central entity for triage and allocation."""
    STATUS_CHOICES = [
        ("incoming", "Incoming Ambulance"),
        ("waiting", "Waiting"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("escalated", "Escalated"),
        ("cancelled", "Cancelled"),
    ]
    TRIAGE_STAGE_CHOICES = [("rapid", "Rapid"), ("structured", "Structured")]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("moderate", "Moderate"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="encounters")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="encounters")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")
    triage_stage = models.CharField(max_length=20, choices=TRIAGE_STAGE_CHOICES, default="rapid")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="moderate")
    risk_score = models.IntegerField(default=0)
    confidence_score = models.IntegerField(default=0)  # 0–100
    assigned_doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_encounters"
    )
    rejection_count = models.IntegerField(default=0)
    version = models.IntegerField(default=1)  # Optimistic locking
    notes = models.TextField(blank=True)
    floor = models.CharField(max_length=50, blank=True, null=True)
    room_number = models.CharField(max_length=50, blank=True, null=True)
    bed_number = models.CharField(max_length=50, blank=True, null=True)
    # Ambulance pre-triage fields
    eta_minutes = models.IntegerField(null=True, blank=True)
    eta_set_at = models.DateTimeField(null=True, blank=True)
    # AI Insight caching — stores GROQ output to avoid repeat calls
    ai_insight_json = models.JSONField(null=True, blank=True)
    # Code Blue state — persistent so alert doesn't re-appear after page reload
    code_blue_active = models.BooleanField(default=False)
    code_blue_acknowledged = models.BooleanField(default=False)
    code_blue_acknowledged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="code_blue_acks"
    )
    code_blue_acknowledged_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "encounters"
        indexes = [
            models.Index(fields=["department", "status"]),
            models.Index(fields=["priority", "created_at"]),
            models.Index(fields=["department", "status", "priority", "created_at"]),
        ]

    def __str__(self):
        return f"Encounter {self.id} — {self.priority} ({self.status})"


class TriageData(models.Model):
    """Triage assessment data linked to an encounter."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(Encounter, on_delete=models.CASCADE, related_name="triage_data")
    vitals_json = models.JSONField(null=True, blank=True)
    # E.g.: {"hr": 120, "spo2": 89, "bp_systolic": 170, "bp_diastolic": 100, "temp": 98.6, "rr": 24, "gcs": 15, "pain_score": 8}
    symptoms_json = models.JSONField(null=True, blank=True)  # list of symptom strings
    red_flag_json = models.JSONField(null=True, blank=True)  # boolean flags
    raw_input_text = models.TextField(null=True, blank=True)  # optional voice/typed input
    llm_processed_json = models.JSONField(null=True, blank=True)  # output from GROQ (never clinical source of truth)
    data_completeness_ratio = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "triagedata"
        indexes = [models.Index(fields=["encounter"])]

    def __str__(self):
        return f"TriageData for encounter {self.encounter_id}"


class AllocationLog(models.Model):
    """Immutable log of every assign / reject / reassign action."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="allocation_logs")
    from_doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="allocations_from"
    )
    to_doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="allocations_to"
    )
    reason = models.TextField(blank=True)
    accepted = models.BooleanField(null=True)  # None = pending, True = accepted, False = rejected
    rejection_reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "allocationlog"
        indexes = [models.Index(fields=["encounter", "timestamp"])]

    def __str__(self):
        return f"Allocation {self.id}: encounter {self.encounter_id} → {self.to_doctor_id}"


class EscalationEvent(models.Model):
    """Records every escalation event with SLA response tracking."""
    TYPE_CHOICES = [
        ("code_blue", "Code Blue"),
        ("trauma_override", "Trauma Override"),
        ("manual_escalation", "Manual Escalation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="escalation_events")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    triggered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="triggered_escalations"
    )
    response_time = models.IntegerField(null=True, blank=True)  # seconds until doctor acknowledges
    acknowledged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_escalations"
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "escalationevent"

    def __str__(self):
        return f"Escalation {self.type} for encounter {self.encounter_id}"


class AuditLog(models.Model):
    """Immutable append-only audit trail for all mutations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    pre_change_snapshot = models.JSONField(null=True, blank=True)
    post_change_snapshot = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata_json = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auditlog"
        indexes = [models.Index(fields=["entity_type", "entity_id", "timestamp"])]

    def save(self, *args, **kwargs):
        # Prevent updates — audit log is append-only
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("AuditLog entries are immutable")
        super().save(*args, **kwargs)


class AnalyticsSnapshot(models.Model):
    """Daily aggregated analytics per department."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="snapshots")
    avg_wait_time = models.FloatField(null=True)
    starvation_count = models.IntegerField(default=0)
    escalation_count = models.IntegerField(default=0)
    throughput = models.IntegerField(default=0)  # encounters completed in the day
    doctor_utilization_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analyticssnapshot"
        unique_together = [("date", "department")]
        indexes = [models.Index(fields=["date", "department"])]


class Assessment(models.Model):
    """Doctor assessment session — notes, media, and LLM-generated report."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encounter = models.OneToOneField(Encounter, on_delete=models.CASCADE, related_name="assessment")
    doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assessments"
    )
    notes = models.TextField(blank=True)
    # List of {name, mime_type, data_b64} dicts — base64 encoded for hackathon simplicity
    media_json = models.JSONField(default=list)
    report_text = models.TextField(blank=True)  # LLM-generated completion report
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assessment"

    def __str__(self):
        return f"Assessment for encounter {self.encounter_id} by {self.doctor_id}"


class HospitalConfig(models.Model):
    """Per-hospital feature flags and configuration, overrides global defaults."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital_name = models.CharField(max_length=200, unique=True)
    feature_flags = models.JSONField(default=dict)  # LLM_ENABLED, VOICE_INPUT_ENABLED, etc.
    avg_revenue_per_patient = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # SLA thresholds in seconds
    sla_code_blue_seconds = models.IntegerField(default=120)  # 2 minutes
    sla_trauma_seconds = models.IntegerField(default=300)     # 5 minutes
    sla_manual_seconds = models.IntegerField(default=900)     # 15 minutes
    max_active_cases_per_doctor = models.IntegerField(default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hospital_config"

    def __str__(self):
        return self.hospital_name

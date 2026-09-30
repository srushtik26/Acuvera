"""
Core serializers: User, Patient, Encounter, TriageData.
"""
from django.utils import timezone
from rest_framework import serializers
from core.models import User, Patient, Encounter, TriageData, Department, HospitalConfig, Assessment


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "profile_type", "starvation_threshold_minutes", "priority_weight_config", "is_active"]


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "clerk_user_id", "email", "full_name", "role",
            "department", "department_name", "is_active",
            "availability_state", "shift_start", "shift_end", "last_assigned_at",
        ]
        read_only_fields = ["id", "clerk_user_id"]

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "external_id", "name", "dob", "age", "gender", "contact_phone", "is_anonymized", "created_at"]


class TriageDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriageData
        fields = [
            "id", "encounter", "vitals_json", "symptoms_json", "red_flag_json",
            "raw_input_text", "llm_processed_json", "data_completeness_ratio", "created_at",
        ]
        read_only_fields = ["id", "encounter", "llm_processed_json", "data_completeness_ratio", "created_at"]


class AssessmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id", "encounter", "doctor", "doctor_name",
            "notes", "media_json", "report_text",
            "started_at", "completed_at",
        ]
        read_only_fields = ["id", "encounter", "doctor", "started_at", "completed_at", "report_text"]

    def get_doctor_name(self, obj):
        return obj.doctor.full_name if obj.doctor else None


class EncounterSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)
    triage_data = TriageDataSerializer(read_only=True)
    assigned_doctor_detail = UserSerializer(source="assigned_doctor", read_only=True)
    has_assessment = serializers.SerializerMethodField()
    assessment_completed = serializers.SerializerMethodField()
    assessment_detail = AssessmentSerializer(source="assessment", read_only=True)
    eta_remaining_seconds = serializers.SerializerMethodField()
    code_blue_acknowledged_by_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = Encounter
        fields = [
            "id", "patient", "patient_detail", "department", "department_name",
            "floor", "room_number", "bed_number",
            "status", "triage_stage", "priority", "risk_score", "confidence_score",
            "assigned_doctor", "assigned_doctor_detail", "rejection_count", "version",
            "notes", "is_deleted", "created_at", "updated_at",
            "triage_data", "has_assessment", "assessment_completed", "assessment_detail",
            "eta_minutes", "eta_set_at", "eta_remaining_seconds",
            "code_blue_active", "code_blue_acknowledged",
            "code_blue_acknowledged_by", "code_blue_acknowledged_at",
            "code_blue_acknowledged_by_name",
        ]
        read_only_fields = ["id", "risk_score", "confidence_score", "version", "created_at", "updated_at"]

    def get_has_assessment(self, obj):
        return hasattr(obj, 'assessment') and obj.assessment is not None

    def get_assessment_completed(self, obj):
        try:
            return obj.assessment.completed_at is not None
        except Exception:
            return False

    def get_eta_remaining_seconds(self, obj):
        """Compute seconds until ambulance arrives. Returns None if not incoming."""
        if obj.status != 'incoming' or not obj.eta_minutes or not obj.eta_set_at:
            return None
        elapsed = (timezone.now() - obj.eta_set_at).total_seconds()
        remaining = (obj.eta_minutes * 60) - elapsed
        return max(int(remaining), 0)

    def get_code_blue_acknowledged_by_name(self, obj):
        if obj.code_blue_acknowledged_by:
            return obj.code_blue_acknowledged_by.full_name
        return None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None


class AnalyzeTriageSerializer(serializers.Serializer):
    """Input for POST /api/triage/{encounter_id}/analyze/"""
    raw_input_text = serializers.CharField(required=False, allow_blank=True)
    vitals = serializers.JSONField(required=False)
    symptoms = serializers.ListField(child=serializers.CharField(), required=False)
    red_flags = serializers.JSONField(required=False)

    def validate(self, data):
        if not data.get("raw_input_text") and not data.get("vitals") and not data.get("symptoms"):
            raise serializers.ValidationError(
                "Provide at least one of: raw_input_text, vitals, or symptoms."
            )
        return data


class HospitalConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalConfig
        fields = "__all__"

"""
Seed management command — creates 3 departments and 1 hospital config.
Run: python manage.py seed_data
"""
import uuid
from django.core.management.base import BaseCommand
from core.models import Department, HospitalConfig


DEPARTMENTS = [
    {
        "name": "General Emergency",
        "profile_type": "general",
        "starvation_threshold_minutes": 30,
        "priority_weight_config": {
            # Vital thresholds
            "SpO2_low_threshold": 90,
            "SpO2_low": 20,
            "HR_high_threshold": 120,
            "HR_high": 15,
            "HR_low_threshold": 50,
            "HR_low": 15,
            "BP_high_threshold": 180,
            "BP_high": 10,
            "pain_threshold": 8,
            "severe_pain": 10,
            "RR_high_threshold": 25,
            "RR_high": 10,
            "temp_high_threshold": 103.0,
            "temp_high": 8,
            "critical_gcs_threshold": 8,
            "critical_spo2_threshold": 85,
            # Patient factors
            "age_over_60": 5,
            # Symptoms
            "symptom_chest_pain": 20,
            "symptom_sweating": 5,
            "symptom_syncope": 15,
            "symptom_altered_mental_status": 15,
            "symptom_severe_headache": 10,
            "symptom_shortness_of_breath": 15,
            "symptom_seizure": 15,
            "symptom_stroke_symptoms": 20,
            "symptom_severe_abdominal_pain": 10,
            "symptom_trauma": 15,
            # Aging
            "aging_minutes_unit": 10,
            "aging_point_unit": 5,
            "min_complete_ratio": 0.6,
            "low_completeness_penalty": 10,
        },
    },
    {
        "name": "Cardiac Emergency",
        "profile_type": "cardiac",
        "starvation_threshold_minutes": 20,
        "priority_weight_config": {
            # Tighter thresholds for cardiac
            "SpO2_low_threshold": 92,
            "SpO2_low": 25,
            "HR_high_threshold": 110,
            "HR_high": 20,
            "HR_low_threshold": 55,
            "HR_low": 20,
            "BP_high_threshold": 170,
            "BP_high": 15,
            "pain_threshold": 7,
            "severe_pain": 15,
            "RR_high_threshold": 22,
            "RR_high": 12,
            "temp_high_threshold": 102.0,
            "temp_high": 8,
            "critical_gcs_threshold": 10,
            "critical_spo2_threshold": 88,
            "age_over_60": 8,
            # Cardiac-specific symptoms weighted higher
            "symptom_chest_pain": 30,
            "symptom_sweating": 10,
            "symptom_syncope": 20,
            "symptom_altered_mental_status": 20,
            "symptom_severe_headache": 8,
            "symptom_shortness_of_breath": 20,
            "symptom_seizure": 12,
            "symptom_stroke_symptoms": 15,
            "symptom_severe_abdominal_pain": 8,
            "symptom_trauma": 10,
            "aging_minutes_unit": 8,
            "aging_point_unit": 7,
            "min_complete_ratio": 0.7,
            "low_completeness_penalty": 15,
        },
    },
    {
        "name": "Trauma Bay",
        "profile_type": "trauma",
        "starvation_threshold_minutes": 15,
        "priority_weight_config": {
            # Trauma — highest urgency defaults
            "SpO2_low_threshold": 94,
            "SpO2_low": 25,
            "HR_high_threshold": 110,
            "HR_high": 15,
            "HR_low_threshold": 60,
            "HR_low": 20,
            "BP_high_threshold": 160,
            "BP_high": 12,
            "pain_threshold": 6,
            "severe_pain": 12,
            "RR_high_threshold": 20,
            "RR_high": 15,
            "temp_high_threshold": 102.0,
            "temp_high": 8,
            "critical_gcs_threshold": 12,
            "critical_spo2_threshold": 90,
            "age_over_60": 5,
            "symptom_chest_pain": 15,
            "symptom_sweating": 5,
            "symptom_syncope": 12,
            "symptom_altered_mental_status": 20,
            "symptom_severe_headache": 12,
            "symptom_shortness_of_breath": 15,
            "symptom_seizure": 15,
            "symptom_stroke_symptoms": 15,
            "symptom_severe_abdominal_pain": 12,
            "symptom_trauma": 25,  # Trauma weighted highest in trauma bay
            "aging_minutes_unit": 5,
            "aging_point_unit": 8,
            "min_complete_ratio": 0.5,
            "low_completeness_penalty": 8,
        },
    },
]

HOSPITAL_CONFIG = {
    "hospital_name": "Acuvera Demo Hospital",
    "feature_flags": {
        "LLM_ENABLED": False,
        "VOICE_INPUT_ENABLED": True,
        "ANALYTICS_ADVANCED": True,
        "FHIR_ENABLED": True,
        "PWA_ENABLED": True,
    },
    "avg_revenue_per_patient": 500,  # INR
    "sla_code_blue_seconds": 120,
    "sla_trauma_seconds": 300,
    "sla_manual_seconds": 900,
    "max_active_cases_per_doctor": 6,
}


class Command(BaseCommand):
    help = "Seed Acuvera with sample departments and hospital config"

    def handle(self, *args, **options):
        self.stdout.write("Seeding departments...")
        created = []
        for dept_data in DEPARTMENTS:
            dept, was_created = Department.objects.get_or_create(
                name=dept_data["name"],
                defaults=dept_data,
            )
            if was_created:
                created.append(dept.name)
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {dept.name}"))
            else:
                # Update config in case it changed
                for k, v in dept_data.items():
                    setattr(dept, k, v)
                dept.save()
                self.stdout.write(f"  [UP] Updated: {dept.name}")

        self.stdout.write("Seeding hospital config...")
        config, was_created = HospitalConfig.objects.get_or_create(
            hospital_name=HOSPITAL_CONFIG["hospital_name"],
            defaults=HOSPITAL_CONFIG,
        )
        if was_created:
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {config.hospital_name}"))
        else:
            self.stdout.write(f"  ~ Already exists: {config.hospital_name}")

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] Seed complete. {len(DEPARTMENTS)} departments, 1 hospital config."
        ))

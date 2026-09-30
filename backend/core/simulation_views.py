"""
Live ER Simulation Engine.
POST /api/admin/simulate/
Floods the ED queue with realistic patients for hackathon demo.
"""
import logging
import random
import time
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAdmin

logger = logging.getLogger("acuvera.simulation")

# ─── Scenario Definitions ────────────────────────────────────────────────────

SCENARIOS = {
    "cardiac_surge": {
        "description": "Cardiac emergency wave — chest pain, tachycardia, hypoxia",
        "patient_templates": [
            {
                "weight": 40,
                "age_range": (45, 80),
                "symptoms": ["chest_pain", "sweating"],
                "vitals": {"hr": (115, 145), "spo2": (87, 93), "bp_systolic": (90, 160), "bp_diastolic": (60, 100), "pain_score": (7, 10)},
                "red_flags": {},
            },
            {
                "weight": 25,
                "age_range": (50, 80),
                "symptoms": ["chest_pain", "shortness_of_breath", "sweating"],
                "vitals": {"hr": (125, 155), "spo2": (84, 90), "bp_systolic": (85, 110)},
                "red_flags": {"cardiac_arrest": False},
            },
            {
                "weight": 20,
                "age_range": (60, 85),
                "symptoms": ["chest_pain", "syncope"],
                "vitals": {"hr": (40, 55), "spo2": (90, 95), "bp_systolic": (80, 100)},
                "red_flags": {},
            },
            {
                "weight": 15,
                "age_range": (30, 60),
                "symptoms": ["shortness_of_breath"],
                "vitals": {"hr": (95, 115), "spo2": (93, 97), "rr": (20, 28)},
                "red_flags": {},
            },
        ],
    },
    "mass_casualty": {
        "description": "Mass casualty event — trauma, hemorrhage, mixed severity",
        "patient_templates": [
            {
                "weight": 30,
                "age_range": (18, 65),
                "symptoms": ["trauma"],
                "vitals": {"hr": (100, 140), "spo2": (85, 93), "bp_systolic": (70, 100), "pain_score": (8, 10)},
                "red_flags": {"severe_hemorrhage": True},
            },
            {
                "weight": 25,
                "age_range": (18, 65),
                "symptoms": ["trauma", "altered_mental_status"],
                "vitals": {"hr": (90, 130), "spo2": (88, 94), "gcs": (6, 10)},
                "red_flags": {},
            },
            {
                "weight": 25,
                "age_range": (18, 65),
                "symptoms": ["trauma"],
                "vitals": {"hr": (80, 110), "spo2": (93, 98), "pain_score": (5, 8)},
                "red_flags": {},
            },
            {
                "weight": 20,
                "age_range": (18, 65),
                "symptoms": ["severe_abdominal_pain"],
                "vitals": {"hr": (85, 105), "spo2": (94, 98), "bp_systolic": (100, 130)},
                "red_flags": {},
            },
        ],
    },
    "pneumonia_cluster": {
        "description": "Respiratory infection cluster — fever, SOB, hypoxia",
        "patient_templates": [
            {
                "weight": 45,
                "age_range": (60, 85),
                "symptoms": ["shortness_of_breath"],
                "vitals": {"hr": (100, 120), "spo2": (88, 93), "rr": (24, 32), "temp": (101.5, 103.5)},
                "red_flags": {},
            },
            {
                "weight": 30,
                "age_range": (40, 75),
                "symptoms": ["shortness_of_breath", "chest_pain"],
                "vitals": {"hr": (108, 125), "spo2": (91, 95), "rr": (22, 28), "temp": (100.5, 102.5)},
                "red_flags": {},
            },
            {
                "weight": 25,
                "age_range": (20, 60),
                "symptoms": ["shortness_of_breath"],
                "vitals": {"hr": (95, 112), "spo2": (93, 97), "rr": (20, 25), "temp": (99.5, 101.5)},
                "red_flags": {},
            },
        ],
    },
    "normal_ops": {
        "description": "Normal ED operations — mixed low-moderate acuity",
        "patient_templates": [
            {
                "weight": 40,
                "age_range": (18, 70),
                "symptoms": ["severe_abdominal_pain"],
                "vitals": {"hr": (75, 100), "spo2": (95, 99), "pain_score": (4, 7)},
                "red_flags": {},
            },
            {
                "weight": 30,
                "age_range": (18, 60),
                "symptoms": ["severe_headache"],
                "vitals": {"hr": (70, 95), "spo2": (96, 99), "bp_systolic": (130, 160)},
                "red_flags": {},
            },
            {
                "weight": 20,
                "age_range": (20, 80),
                "symptoms": ["syncope"],
                "vitals": {"hr": (65, 90), "spo2": (95, 98), "bp_systolic": (95, 125)},
                "red_flags": {},
            },
            {
                "weight": 10,
                "age_range": (18, 45),
                "symptoms": ["trauma"],
                "vitals": {"hr": (80, 105), "spo2": (95, 99), "pain_score": (3, 6)},
                "red_flags": {},
            },
        ],
    },
}

FIRST_NAMES = ["Ramesh", "Priya", "Vikram", "Sunita", "Arjun", "Meera", "Suresh",
               "Kavita", "Anil", "Pooja", "Rajesh", "Anita", "Deepak", "Rekha",
               "Amit", "Sonia", "Manoj", "Geeta", "Vinod", "Nisha", "Rohit", "Seema"]
LAST_NAMES = ["Kumar", "Sharma", "Patel", "Singh", "Gupta", "Verma", "Mishra",
              "Joshi", "Agarwal", "Rao", "Nair", "Pillai", "Reddy", "Mehta"]


def _random_template(templates):
    """Weighted random selection of a patient template."""
    weights = [t["weight"] for t in templates]
    return random.choices(templates, weights=weights, k=1)[0]


def _rand_vital(vrange):
    """Random value in a range tuple."""
    lo, hi = vrange
    if isinstance(lo, float) or isinstance(hi, float):
        return round(random.uniform(lo, hi), 1)
    return random.randint(int(lo), int(hi))


class SimulateView(APIView):
    """POST /api/admin/simulate/"""
    permission_classes = [IsAdmin]

    def post(self, request):
        scenario_key = request.data.get("scenario", "normal_ops")
        patient_count = min(int(request.data.get("patient_count", 20)), 60)
        stagger_delay = float(request.data.get("stagger_ms", 150)) / 1000.0

        if scenario_key not in SCENARIOS:
            return err(f"Unknown scenario. Choose from: {list(SCENARIOS.keys())}", 400)

        from core.models import Department, Patient, Encounter
        from triage.engine import compute_triage

        dept = Department.objects.filter(is_active=True).first()
        if not dept:
            return err("No active department found.", 400)

        scenario = SCENARIOS[scenario_key]
        templates = scenario["patient_templates"]

        results = {
            "scenario": scenario_key,
            "description": scenario["description"],
            "patients_created": 0,
            "priority_distribution": {"critical": 0, "high": 0, "moderate": 0, "low": 0},
            "escalations_triggered": 0,
            "encounter_ids": [],
        }

        start_time = time.time()

        for i in range(patient_count):
            try:
                tmpl = _random_template(templates)
                age = random.randint(*tmpl["age_range"])
                gender = random.choice(["male", "female"])
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

                # Build vitals with noise
                vitals = {}
                for k, vrange in tmpl.get("vitals", {}).items():
                    vitals[k] = _rand_vital(vrange)

                symptoms = list(tmpl.get("symptoms", []))
                # Randomly add 1 extra symptom for realism
                bonus_symptoms = ["sweating", "altered_mental_status", "severe_headache"]
                if random.random() < 0.25:
                    symptoms.append(random.choice(bonus_symptoms))

                red_flags = {k: v for k, v in tmpl.get("red_flags", {}).items() if v}

                # Create patient + encounter
                patient = Patient.objects.create(
                    name=name, age=age, gender=gender
                )
                enc = Encounter.objects.create(
                    patient=patient,
                    department=dept,
                    status="waiting",
                    notes=f"[sim:{scenario_key}]",
                )

                # Run triage immediately
                triage_result = compute_triage(
                    encounter_id=str(enc.id),
                    vitals=vitals,
                    symptoms=symptoms,
                    red_flags=red_flags,
                    patient_age=age,
                )
                priority = triage_result["priority"]
                results["priority_distribution"][priority] += 1

                # Auto-assign if doctors available
                try:
                    from allocation.engine import auto_allocate
                    auto_allocate(str(enc.id))
                except Exception:
                    pass

                # Trigger escalation for Code Blue candidates
                if red_flags.get("severe_hemorrhage") or red_flags.get("cardiac_arrest"):
                    try:
                        from escalation.engine import trigger_escalation
                        trigger_escalation(
                            encounter_id=str(enc.id),
                            escalation_type="code_blue",
                            reason=f"Simulation: {scenario_key}",
                        )
                        results["escalations_triggered"] += 1
                    except Exception:
                        pass

                results["patients_created"] += 1
                results["encounter_ids"].append(str(enc.id))

                # Staggered arrival for visual effect
                if stagger_delay > 0 and i < patient_count - 1:
                    time.sleep(stagger_delay)

            except Exception as e:
                logger.warning("Simulation patient %d failed: %s", i, e)

        results["time_ms"] = round((time.time() - start_time) * 1000)
        logger.info(
            "Simulation complete: scenario=%s patients=%d escalations=%d time=%dms",
            scenario_key, results["patients_created"],
            results["escalations_triggered"], results["time_ms"]
        )

        return ok(results, status=201)

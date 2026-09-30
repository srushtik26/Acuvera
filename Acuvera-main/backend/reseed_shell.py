from core.models import Encounter, Patient, Department
from triage.engine import compute_triage

dept = Department.objects.filter(is_active=True).first()
if not dept:
    print("ERROR: No active department")
else:
    print(f"Dept: {dept.name}")
    scenarios = [
        {'name': 'Ramesh Kumar',  'age': 68, 'gender': 'male',   'syms': ['chest_pain', 'sweating'],            'vitals': {'hr': 128, 'spo2': 88, 'bp_systolic': 92,  'pain_score': 9}},
        {'name': 'Priya Sharma',  'age': 45, 'gender': 'female', 'syms': ['stroke_symptoms', 'altered_mental_status'], 'vitals': {'hr': 115, 'spo2': 91, 'gcs': 11}},
        {'name': 'Vijay Singh',   'age': 35, 'gender': 'male',   'syms': ['trauma'],                            'vitals': {'hr': 105, 'spo2': 94, 'bp_systolic': 110, 'pain_score': 7}},
        {'name': 'Sunita Patel',  'age': 72, 'gender': 'female', 'syms': ['shortness_of_breath'],               'vitals': {'hr': 112, 'spo2': 93, 'rr': 26, 'temp': 102.1}},
        {'name': 'Arjun Mehta',   'age': 28, 'gender': 'male',   'syms': ['severe_headache'],                   'vitals': {'hr': 88,  'spo2': 97, 'bp_systolic': 145}},
        {'name': 'Meera Rao',     'age': 55, 'gender': 'female', 'syms': ['severe_abdominal_pain'],             'vitals': {'hr': 95,  'spo2': 96, 'pain_score': 6}},
        {'name': 'Deepak Nair',   'age': 62, 'gender': 'male',   'syms': ['syncope'],                          'vitals': {'hr': 58,  'spo2': 94, 'bp_systolic': 98}},
        {'name': 'Anita Reddy',   'age': 41, 'gender': 'female', 'syms': ['chest_pain'],                       'vitals': {'hr': 118, 'spo2': 95, 'bp_systolic': 155, 'pain_score': 8}},
        {'name': 'Suresh Joshi',  'age': 19, 'gender': 'male',   'syms': ['trauma'],                           'vitals': {'hr': 92,  'spo2': 98, 'pain_score': 4}},
        {'name': 'Kavita Gupta',  'age': 77, 'gender': 'female', 'syms': ['altered_mental_status', 'shortness_of_breath'], 'vitals': {'hr': 122, 'spo2': 90, 'gcs': 12, 'temp': 101.8}},
    ]
    for s in scenarios:
        try:
            p = Patient.objects.create(name=s['name'], age=s['age'], gender=s['gender'])
            enc = Encounter.objects.create(patient=p, department=dept, status='waiting', notes='[reseed]')
            r = compute_triage(str(enc.id), s['vitals'], s['syms'], {}, s['age'])
            print(f"  + {s['name']} -> {r['priority'].upper()} score={r['effective_score']}")
        except Exception as ex:
            print(f"  ERR {s['name']}: {ex}")
    total = Encounter.objects.filter(is_deleted=False).count()
    print(f"Total encounters now: {total}")

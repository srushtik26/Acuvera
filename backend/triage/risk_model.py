import math
from datetime import datetime
from django.utils import timezone as dj_tz


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def icu_logit(v, syms, age):
    logit = -2.5
    d = []
    
    s = v.get("spo2")
    if s is not None:
        if s < 85:   logit += 1.8; d.append(("Critical hypoxia SpO₂ < 85%", 1.8))
        elif s < 92: logit += 1.1; d.append(("Hypoxia SpO₂ < 92%", 1.1))
        elif s < 95: logit += 0.4; d.append(("Borderline SpO₂ < 95%", 0.4))
        
    hr = v.get("hr")
    if hr is not None:
        if hr > 130:   logit += 1.5; d.append(("Severe tachycardia", 1.5))
        elif hr > 110: logit += 0.9; d.append(("Tachycardia", 0.9))
        elif hr < 45:  logit += 1.6; d.append(("Severe bradycardia", 1.6))
        elif hr < 55:  logit += 0.8; d.append(("Bradycardia", 0.8))
        
    sbp = v.get("bp_systolic")
    if sbp is not None:
        if sbp < 80:   logit += 1.9; d.append(("Severe hypotension", 1.9))
        elif sbp < 90: logit += 1.2; d.append(("Hypotension", 1.2))
        
    rr = v.get("rr")
    if rr is not None:
        if rr > 30:   logit += 1.3; d.append(("Severe tachypnea", 1.3))
        elif rr > 24: logit += 0.7; d.append(("Tachypnea", 0.7))
        
    gcs = v.get("gcs")
    if gcs is not None:
        if gcs <= 8:   logit += 2.0; d.append(("Severely depressed GCS", 2.0))
        elif gcs <= 12:logit += 1.0; d.append(("Altered consciousness", 1.0))
        
    for sym, w, lbl in [("chest_pain", 0.8, "Chest pain"), ("shortness_of_breath", 0.7, "Dyspnea"),
                        ("stroke_symptoms", 1.2, "Stroke"), ("seizure", 0.9, "Seizure"),
                        ("altered_mental_status", 0.9, "AMS"), ("syncope", 0.6, "Syncope")]:
        if sym in syms:
            logit += w
            d.append((lbl, w))
            
    if age:
        if age >= 80:   logit += 0.9
        elif age >= 65: logit += 0.5
        elif age >= 60: logit += 0.3
        
    return logit, d


def resp_logit(v, syms):
    logit = -3.0
    d = []
    
    s = v.get("spo2")
    if s is not None:
        if s < 85:   logit += 2.5
        elif s < 90: logit += 1.8
        elif s < 92: logit += 1.0
        
    rr = v.get("rr")
    if rr is not None:
        if rr > 30:   logit += 1.8
        elif rr > 24: logit += 1.0
        elif rr < 10: logit += 1.5
        
    if "shortness_of_breath" in syms: logit += 1.0
    if "seizure" in syms:             logit += 0.7
    
    gcs = v.get("gcs")
    if gcs is not None and gcs <= 8: logit += 1.2
    
    return logit, d


def card_logit(v, syms, age):
    logit = -3.2
    d = []
    
    if "chest_pain" in syms: logit += 2.0
    if "sweating"   in syms: logit += 1.0
    if "syncope"    in syms: logit += 0.9
    
    hr = v.get("hr")
    if hr is not None:
        if hr > 130:   logit += 1.3
        elif hr > 110: logit += 0.7
        elif hr < 45:  logit += 1.4
        
    sbp = v.get("bp_systolic")
    if sbp is not None:
        if sbp < 90:     logit += 1.2
        elif sbp >= 180: logit += 0.9
        
    s = v.get("spo2")
    if s is not None and s < 90: logit += 0.8
    
    if age:
        if age >= 75:   logit += 1.0
        elif age >= 60: logit += 0.5
        
    return logit, d


def compute_risk_prediction(vitals, symptoms, patient_age, triage_score=0):
    """
    Computes clinical deterioration risk metrics based on vitals, symptoms, age, and existing score.
    Returns dictionary with structured output.
    """
    vitals = vitals or {}
    symptoms = symptoms or []
    
    # Clean symptoms to match logic checks
    syms = [s.lower().replace(" ", "_") for s in symptoms]
    
    il, icu_drivers = icu_logit(vitals, syms, patient_age)
    rl, _ = resp_logit(vitals, syms)
    cl, _ = card_logit(vitals, syms, patient_age)
    
    icu_p  = sigmoid(il) * 100
    resp_p = sigmoid(rl) * 100
    card_p = sigmoid(cl) * 100
    
    det = (0.45 * sigmoid(il) + 0.30 * sigmoid(cl) + 0.25 * sigmoid(rl)) * 100
    
    if triage_score > 0:
        det = 0.7 * det + 0.3 * (min(triage_score, 100) / 100) * 100
        
    level = "CRITICAL" if det >= 65 else "HIGH" if det >= 40 else "MODERATE" if det >= 20 else "LOW"
    
    # Sort and format top risk drivers for display
    # calculate top drivers correctly by sorting their raw weight impacts or keeping driver tuples
    sorted_drivers = sorted(icu_drivers, key=lambda x: x[1], reverse=True)[:5]
    top_drivers = []
    
    # convert weights to rough percentages for display like in the mock
    for lbl, w in sorted_drivers:
        # A rough heuristic translation of logit weight to percentage contribution
        impact_pct = int(w / max(il, 0.1) * 100) if il > 0 else int(w * 10)
        # Cap to look reasonable, e.g. Max 45% per individual driver
        impact_pct = min(impact_pct, 45)
        top_drivers.append({
            "label": lbl,
            "impact_percentage": impact_pct,
            "direction": "up" # since these risk factors generally increase risk
        })
        
    return {
        "overall_deterioration_risk": round(det, 1),
        "risk_level": level,
        "icu_probability": round(icu_p, 1),
        "respiratory_failure_risk": round(resp_p, 1),
        "cardiac_event_risk": round(card_p, 1),
        "top_risk_drivers": top_drivers,
        "prediction_generated_at": dj_tz.now().isoformat()
    }

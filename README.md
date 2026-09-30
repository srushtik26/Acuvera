# Acuvera 🏥 
**Emergency Department Operational Intelligence & Triage Optimization Platform**

---

## 📑 Table of Contents
1. [Executive Summary & Core Mission](#1-executive-summary--core-mission)
2. [The Problem Statement: Crisis in the Emergency Department](#2-the-problem-statement-crisis-in-the-emergency-department)
3. [What We Built: The Acuvera Solution](#3-what-we-built-the-acuvera-solution)
4. [Engine 1: The Intelligent Triage & Risk Prediction Engine](#4-engine-1-the-intelligent-triage--risk-prediction-engine)
5. [Engine 2: The Workload-Aware Doctor Allocation Engine](#5-engine-2-the-workload-aware-doctor-allocation-engine)
6. [Engine 3: Starvation Protection & SLA Adherence](#6-engine-3-starvation-protection--sla-adherence)
7. [Engine 4: High-Stakes Escalation & Interruption Handling](#7-engine-4-high-stakes-escalation--interruption-handling)
8. [Engine 5: Post-Encounter LLM Processing & Medical Scribing](#8-engine-5-post-encounter-llm-processing--medical-scribing)
9. [Engine 6: Executive Operations & AI Insight Assistant](#9-engine-6-executive-operations--ai-insight-assistant)
10. [Technical Architecture & Strict Constraints](#10-technical-architecture--strict-constraints)
11. [Step-by-Step Validation & Demo Guide](#11-step-by-step-validation--demo-guide)

---

## 1. Executive Summary & Core Mission
Emergency Departments (EDs) are inherently chaotic, high-stakes environments. While clinical staff are thoroughly trained to handle medical emergencies, the underlying operational logistics of an ED often act as a massive, invisible bottleneck. In resource-constrained settings, such as high-volume Indian hospitals, these logistical failures directly translate to increased morbidity and mortality.

**Acuvera** is a full-stack, India-optimized Emergency Department Operational Intelligence & Triage Optimization Platform. It intercepts, evaluates, routes, and monitors ED patient encounters with mathematical precision. 

**Crucially:** Acuvera is a **Decision-Support and Operational Engine**, not a diagnostic authority. It **never diagnoses or prescribes treatment**. All triage and allocation logic is deterministically coded, explainable, and fully compliant with the directive to act as an orchestrator, rather than a robotic doctor. It exists to assist, not replace, clinical judgment.

---

## 2. The Problem Statement: Crisis in the Emergency Department
The development of Acuvera was driven by five massive, systemic failures commonly found in modern EDs.

### 2.1 The Triage Bottleneck and Subjective Bias
When dozens of patients flood an ED, nurses must perform Rapid Triage. However, subjective human judgment, exhaustion, varied experience levels, and communication barriers lead to wildly inconsistent prioritization. A patient complaining of "chest pain" might be correctly fast-tracked by a veteran nurse, but incorrectly assigned a lower priority by a junior nurse who focuses instead on a louder, but non-critical, patient. There is no mathematical baseline ensuring that patients are scored fairly based on their actual physiological vitals.

### 2.2 Blind & Inequitable Doctor Allocation
In many EDs, the "Assign to Doctor" process is highly flawed. Nurses either assign patients round-robin, or they assign them to whichever doctor is physically closest or most familiar. This leads to profound workload imbalances. Doctor A might be drowning with 4 active "Critical" patients, while Doctor B plays on their phone with a single "Low" priority patient. This imbalance leads to physician burnout and catastrophic delays in care for Doctor A's patients.

### 2.3 The "Patient Starvation" Phenomenon
As high-priority and critical patients continuously arrive, patients categorized as "Moderate" or "Low" priority are perpetually pushed down the queue. A patient might safely wait 45 minutes, but if they wait 6 hours because they keep getting bypassed, their condition may covertly deteriorate into a critical state. This "starvation" is rarely tracked in real-time until the patient collapses in the waiting room.

### 2.4 Escalation Chaos & SLA Breaches
When a "Code Blue" or "Trauma Override" occurs, panic ensues. The communication is often verbal or relying on overhead PA systems. It is extremely difficult for administrators to track exactly *when* the Code Blue was triggered, *who* responded, and *how long* it took the assigned physician to acknowledge the escalation. Service Level Agreements (SLAs) are breached routinely without any trail of accountability.

### 2.5 Infrastructure Reality: Connectivity Dead Zones
Hospitals are notorious for their thick concrete walls, lead-lined radiology departments, and overloaded Wi-Fi networks. Modern web-based health applications simply crash or lose data when the internet connection drops for even a few seconds. If a nurse spends 3 minutes carefully taking a patient's vitals and typing out a chief complaint, a network drop means losing that critical data and delaying triage.

---

## 3. What We Built: The Acuvera Solution
To combat these five pillars of operational failure, we designed Acuvera from the ground up as a multi-engine orchestrator. We built dedicated, sandboxed logic engines to solve each problem, tying them together with a unified React Frontend and a robust Django/PostgreSQL backend.

### 3.1 Decision-Support, Not Diagnosis
Acuvera explicitly avoids the legal and ethical quagmires of autonomous medical systems. Every LLM generation is marked with a disclaimer. The platform focuses solely on operations. If Acuvera goes offline, the hospital simply reverts to paper; no life-saving diagnostic machinery is disrupted.

### 3.2 Key Target Audiences
- **Triage Nurses:** Armed with a tablet, entering vitals, utilizing voice dictation, and trusting the engine to route the patient to the fairest doctor.
- **ED Physicians (Doctors):** Viewing a streamlined dashboard of their assigned cases, receiving undeniable, pulsing alerts for escalations, and having their charting time slashed by AI summarization.
- **Hospital Administrators:** Utilizing the immutable `AuditLog` and `EscalationEvent` tables in the database to review SLA breaches and resource utilization.

---

## 4. Engine 1: The Intelligent Triage & Risk Prediction Engine
The first module a user interacts with is the Triage Engine. Its job is to take unstructured and structured input from the nurse and return a strict, deterministic Priority.

### 4.1 Deterministic Clinical Rules Matrix
When a nurse inputs a set of variables (`vitals` such as Heart Rate, SpO2, Blood Pressure, GCS; `symptoms` such as chest pain, sweating; and `raw text`), the backend Triage Engine executes a hardcoded ruleset. It evaluates thresholds (e.g., `spO2 < 90` -> `+30 points`, `HR > 120` -> `+20 points`). This ensures that no matter who the nurse is, a SpO2 of 88% will *always* trigger a high risk score. The output is a calculated `effective_score` mapped to a defined priority level (Low, Moderate, High, Critical).

### 4.2 Web Speech API (Voice-to-Text Dictation)
To speed up the Rapid Triage process, we integrated the browser-native `Web Speech API`. Nurses can click "🎙️ Dictate" on the Triage Modal and speak the patient's chief complaint. Because Acuvera is optimized for India, the Speech Recognition engine is explicitly configured to use `lang = 'en-IN'`, allowing it to accurately transcribe Hinglish dialects (e.g., "Seena mein dard ho raha hai aur saas lene mein takleef"). This leaves the nurse's hands free to place pulse oximeters and blood pressure cuffs.

### 4.3 Hard Overrides & Red Flags
If a nurse selects a critical "Red Flag" (such as `cardiac_arrest` or `airway_compromised`), the Triage Engine completely bypasses the mathematical score calculation. It instantly forces a **HARD OVERRIDE**, setting the priority to `CRITICAL` and the score to the maximum ceiling (100+), ensuring the patient is immediately pushed to the absolute top of the queue.

### 4.4 The Offline PWA Mode (IndexedDB Caching)
To solve the "Connectivity Dead Zone" problem, Acuvera is structured as a Progressive Web App (PWA). If the nurse is in the middle of triaging a patient and the Wi-Fi drops:
1. The frontend (`navigator.onLine` check) detects the outage.
2. Instead of calling the API and crashing, it serializes the entire form (vitals, text, red flags) and writes it securely to the browser's local **IndexedDB** using the `idb` wrapper.
3. A yellow banner alerts the nurse that the app is offline but safely caching drafts.
4. The moment connectivity is restored, a `Sync Offline Drafts` button appears. Clicking it iterates through IndexedDB, silently posts all cached payloads to the backend, calculates their triage scores, clears the local cache, and seamlessly injects them into the live queue. No data is ever lost.

### 4.5 Generating Printable Triage Slips
Not all workflows are purely digital. Once Triage is complete, the nurse can click "🖨️ Print Slip". This generates a clean, printable HTML document summarizing the patient's identifiers, the exact time, the calculated Priority/Score, the contributing rules (e.g., "Tachycardia detected: HR > 120"), and a disclaimer. This physical piece of paper can be pinned to the patient's bed or chart.

---

## 5. Engine 2: The Workload-Aware Doctor Allocation Engine
Once a patient is triaged, they must be assigned a doctor. This is where Acuvera shines, replacing manual assignment with mathematically fair workload distribution.

### 5.1 The Mathematical Model of Workload
The Allocation Engine calculates a live `workload_score` for every `active` doctor in the required department who is currently `on_shift`. 
The formula is:
```python
workload_score = (count_of_critical_patients * 10) +
                 (count_of_high_patients * 5) +
                 (count_of_moderate_patients * 2) +
                 (count_of_low_patients * 1)
```
When a nurse requests a doctor suggestion, the engine queries all valid doctors, sorts them by this `workload_score` ascending, and suggests the doctor with the absolute lowest burden. This prevents highly efficient doctors from being punished with endless assignments.

### 5.2 Concurrency & Transaction Safety
EDs operate at high concurrency. What happens if two nurses try to fetch the "least burdened doctor" at the exact same millisecond? 
Acuvera solves this using PostgreSQL's row-level locking. We wrap the assignment inside a `transaction.atomic()` block and execute a `SELECT FOR UPDATE` query on the Encounter row. We also utilize optimistic locking via a `version` integer field. If an encounter is modified by Nurse A while Nurse B is looking at it, Nurse B's request will safely reject, preventing double-booking or corrupt state.

### 5.3 Acceptance, Rejection, and Penalties
Allocation is a two-way street. When a case is assigned, it sits in the Doctor's "Pending Assignments" queue. 
- The Doctor must explicitly click **Accept** to move it to their active queue.
- The Doctor may click **Reject** (requiring a text reason). If rejected, the Encounter's `rejection_count` increments. The Allocation Engine is aware of rejections; highly-rejected encounters eventually trigger administrative audits to figure out why no physician wants to take the case.

### 5.4 The Smart Referral System
Sometimes a doctor accepts a case, assesses the patient, and realizes they are the wrong specialist. The Doctor Dashboard includes a **🔄 Refer** button. 
Clicking this triggers a specialized Allocation API request that suggests a *different* doctor in the *same department*. The system guarantees it will never suggest the doctor who is currently trying to refer the patient, successfully passing the baton to the next fairest colleague.

---

## 6. Engine 3: Starvation Protection & SLA Adherence
The queue cannot remain static. Acuvera actively monitors the waiting times of every unassigned patient to prevent "Patient Starvation".

### 6.1 Real-Time Queue Scanning & Starvation Thresholds
Each Department in Acuvera has a configurable `starvation_threshold_minutes` (e.g., 60 minutes for General Emergency, 15 minutes for Cardiac). The frontend and backend continuously poll the timestamps of Encounters in the `waiting` state. 

### 6.2 The "⚠️ Too Long" UI Indicators
If `(Current Time - Encounter Created At) > starvation_threshold`, the Nurse's Active Queue visually updates. A `⚠️ Too long` banner replaces the standard wait time text to immediately draw the nurse's eye to the starving patient.

### 6.3 Forced Reassignment Protocol
To rectify the starvation, the nurse is presented with a specialized **⚠️ Reassign** action button. This button utilizes the Allocation Engine to force a new calculation, bypassing standard priority queues to immediately assign the starving patient to the nearest available doctor, ensuring the patient is seen before their condition unexpectedly worsens.

---

## 7. Engine 4: High-Stakes Escalation & Interruption Handling
When a patient suddenly codes or a trauma patient rolls through the doors, standard queues are entirely irrelevant. Acuvera handles this with its dedicated Escalation capabilities.

### 7.1 Code Blue & Trauma Override Workflows
A nurse can click the bright red `🚨 Code Blue` button on *any* patient in the queue. This instantly creates an `EscalationEvent` on the backend, bypassing all triage logic.

### 7.2 The Escalation Alert Banner & Real-Time Polling
When an Escalation Event is tied to an encounter, and that encounter belongs to a specific doctor, the Doctor's Dashboard transforms. At the absolute top of their screen, a massive, `pulse-border` animated red banner appears. It screams:
**"🚨 CRITICAL ESCALATION: Code Blue triggered for [Patient Name]"**
It displays a live, ticking timer ticking up every single second (e.g., `00:00:14 ... 00:00:15`).

### 7.3 Acknowledgment, Response Times, and SLA Metrics
The banner only disappears when the physician physically clicks the **"I Am Responding"** button. This sends an acknowledgment payload to the backend. The Escalation Engine calculates the exact `response_time` in seconds. It compares this against the hospital's strict Service Level Agreement (SLA, e.g., 60 seconds). If breached, `sla_breached` is set to `True`, creating a permanent, undisputable audit trail for hospital administrators to review why the response was delayed.

---

## 8. Engine 5: Post-Encounter LLM Processing & Medical Scribing
Taking notes and writing clinical summaries consumes a massive portion of a physician's shift. Acuvera safely delegates this mundane scribing task to Artificial Intelligence.

### 8.1 The Doctor Assessment Module
Once a doctor has seen the patient, they click "🩺 Assess" on the dashboard. This opens an Assessment Modal where they view the patient's exact physical location (Floor, Room, Bed, passed directly from the nurse's intake). The doctor can type their raw clinical notes, examinations, and final thoughts, and they can upload images (e.g., photos of a rash or EKG readouts).

### 8.2 Safe AI: PHI Stripping and Feature Flagging
Acuvera respects patient privacy. Before any data touches a third-party server, the backend employs a strict PHI (Protected Health Information) stripping utility. Patient names, exact birthdates, phone numbers, and identifying strings are actively regex-stripped from the payload. Furthermore, the entire LLM feature is wrapped in a dynamic feature flag `LLM_ENABLED`, allowing administrators to disable the AI entirely during cloud outages or privacy audits without breaking the core application.

### 8.3 Integration with GROQ Cloud API
When the doctor marks the assessment as "Done ✓", an asynchronous background task is spawned (`APScheduler`). It aggregates:
1. The Nurse's original Triage payload (Vitals, Symptoms).
2. The Nurse's Voice Dictation text.
3. The newly entered Doctor's Notes.
It packages this into a highly optimized prompt and fires it via the ultra-low latency GROQ Cloud API (utilizing Llama 3 / Mixtral models). 

### 8.4 Deterministic Output Structuring
The prompt aggressively forces the LLM to output ONLY valid JSON. It demands specific fields: `chief_complaint`, `clinical_summary`, `suggested_investigations`, and `disclaimer`. 
The backend catches this JSON, validates it against the schema, and saves it to the database. 

To ensure maximum readability, both the **Doctor Dashboard (Patient History)** and **Nurse Dashboard (Report Viewer)** utilize a custom `<FormattedReport />` React component. This component dynamically parses incoming ASCII text, detects section dividers, strips redundant fallback data, and renders a deeply styled, glassmorphism-inspired clinical report with distinct headers and key-value chips.

---

## 9. Engine 6: Executive Operations & AI Insight Assistant
While clinical staff require patient-specific data, Hospital Administrators require macro-level operational telemetry.

### 9.1 The Operations AI Assistant
The Admin Dashboard features a persistent, floating AI Chatbot positioned at the bottom right. This bot acts as the hospital's "Operations Chief."
When opened, the frontend automatically bundles a live JSON payload containing real-time metrics:
- Active Patient Count
- Critical Case Count
- Starved Cases (SLA Breaches)
- Average Wait Times & Queue Load
- Live Doctor Utilization Percentages

### 9.2 Context-Aware Answers & Hallucination Defense
The AI Assistant processes this deterministic payload alongside the Administrator's prompt (e.g., *"Why are wait times so high?"*). 
To prevent dangerous LLM hallucinations, the backend enforces a massive system prompt override: it strictly defines "Starvation" as an SLA wait-time breach (not a lack of food), and explicitly commands the engine to only formulate answers derived from the provided structural metrics, keeping responses authoritative and actionable.

### 9.3 Deterministic Offline Mode
If the GROQ Cloud connection drops or the `LLM_ENABLED` feature flag is explicitly turned off via the database, the AI Assistant does not crash. It intercepts the failure and dynamically generates a beautifully formatted, Markdown-powered "Hospital Operations Summary" directly from local deterministic telemetry, parsing prompts for keywords (like "Wait", "Starving", "Staff") to intelligently route offline responses.

---

## 10. Technical Architecture & Strict Constraints
Acuvera was built adhering to extremely strict technological boundaries to ensure deployability, stability, and maintainability.

### 9.1 The Backend (Django + PostgreSQL)
- **Django 4.x:** Provides a vastly stable ORM and routing layer. We lean heavily into Django's structured models to cleanly map our complex business logic.
- **Django REST Framework (DRF):** Powers our entire API layer, utilizing strictly defined ModelSerializers to validate inbound JSON.
- **PostgreSQL 14+:** The absolute backbone of Acuvera. We utilize its advanced JSONB field types to store dynamic triage data, heavily rely on its indexing for queue performance, and depend entirely on its ACID compliance for `SELECT FOR UPDATE` transaction row-locking.

### 9.2 Background Task Orchestration (APScheduler)
Traditional architectures use Celery + Redis for background jobs, significantly complicating deployment and infrastructure costs. Acuvera utilizes `APScheduler` to run asynchronous jobs entirely in-process within the Django application footprint, minimizing points of failure while reliably handling LLM queues and starvation polling.

### 9.3 Custom JWT Auth (Clerk)
User authentication is delegated to Clerk via strict JWTs. The backend validates the asymmetric signatures of inbound tokens. This was chosen specifically because the JWT adapter interface can be trivially swapped out for enterprise SAML or LDAP integrations commonly required by large hospital networks.

### 9.4 The Frontend (React + Vite)
- We utilize React for its predictable component lifecycle and Vite for sub-second Hot Module Reloading (HMR). 
- The entire frontend is styled using custom, deeply-layered Vanilla CSS variables. We rely on CSS custom properties for rich thematic toggles, dynamic pulsing animations, and a cohesive, premium glassmorphism aesthetic that avoids feeling like a cheap legacy dashboard.
- Installed as a PWA, granting the app native performance characteristics on hospital tablets.

### 9.5 State Management & API Layer
- **Zustand:** Provides ultra-lightweight, boilerplate-free global state management for the user session and authentication tokens.
- **Axios:** A strictly configured Axios client acts as the central API gateway, automatically injecting Authorization headers and neatly parsing JSON errors for the UI to consume.
- **IndexedDB / idb:** Ensures offline resilience.

---

## 10. Step-by-Step Validation & Demo Guide
To truly understand Acuvera, you must run it. Follow these specific verification workflows to witness the engines in action.

### 10.1 Running the Environment
Ensure both servers are running. 
1. `cd backend && python manage.py runserver`
2. `cd frontend && npm run dev`
*(Populate your `.env` files with the requisite GROQ and Clerk keys before starting).*

### 10.2 Demo 1: The Disconnected Triage
**Goal:** Prove offline resilience.
1. Log in as a Nurse and navigate to the Active Queue.
2. Disconnect your computer from Wi-Fi (or throttle your Network tab in Chrome DevTools to "Offline").
3. Click `+ New Patient`, register a patient, and open an encounter.
4. Click `Triage`. Enter a heart rate of 150 and click `🔬 Analyze`.
5. Observe the UI alert notifying you that you are offline and the draft is cached. Note the yellow banner dynamically appearing at the top of the queue.
6. Reconnect your Wi-Fi. 
7. Click the new `⚠️ Sync 1 Offline Drafts` button on the Nurse Dashboard. Watch the system silently submit the payload, delete the cache, and display the prioritized patient.

### 10.3 Demo 2: The Unfair Workload Defense
**Goal:** Prove deterministic allocation fairness.
1. Open two browser windows. Log in as Nurse A in one, and Doctor B in the other.
2. Nurse A creates 3 patients, deliberately scoring them as "Moderate" priority. 
3. Assign all 3 patients to Doctor B.
4. Watch Doctor B's "Pending Assignments" overflow. 
5. Nurse A creates a 4th patient. When Nurse A clicks "Assign", watch the system completely bypass Doctor B (who has a terrible workload score) and suggest a different, unburdened doctor.

### 10.4 Demo 3: Saving the Starving Patient
**Goal:** Prove starvation tracking logic.
1. To speed up testing, temporarily edit the backend `Department` model to set a `starvation_threshold_minutes` to `0`. 
2. As a Nurse, create a new low-priority patient and assign them to a doctor. Wait a few seconds for polling to occur.
3. Observe the `Wait` column on the nurse dashboard transition to a glaring `⚠️ Too long` indicator.
4. Observe the appearance of the context-aware `⚠️ Reassign` action button, explicitly built to rescue this specific patient.

### 10.5 Demo 4: The 15-Second Code Blue
**Goal:** Prove the sub-second escalation architecture.
1. Have a Nurse and the Assigned Doctor dashboards open side-by-side.
2. The Nurse clicks the bright red `🚨 Code Blue` button on the patient's queue row.
3. Keep your eyes on the Doctor's Dashboard. Within 5 seconds (via polling), a massive, pulsing red banner will inject itself globally at the top of the app. The timer will actively count up.
4. Wait exactly 15 seconds.
5. The Doctor clicks `I Am Responding`. Observe the banner vanish, guaranteeing that the exact `response_time` of 15 seconds was successfully intercepted and written to the immutable Postgres Audit tables.

### 10.6 Demo 5: From Assessment to LLM Report
**Goal:** Prove the Ethical AI loop.
1. The Doctor clicks `🩺 Assess` on an active case.
2. The Doctor enters brief, shorthand clinical notes (e.g., "Pt breathless. Crackles lower lobes. Given O2."). 
3. The Doctor clicks `Done ✓`. 
4. Switch back to the Nurse Dashboard. Click the blue `📋 Report` button that has now appeared next to the completed case.
5. Observe the breathtaking, highly sanitized, structurally perfect medical summary generated deterministically by the GROQ Mixtral model, consolidating the Nurse's raw intake with the Doctor's shorthand notes into a cohesive clinical report.

---
**End of Acuvera Implementation Specification.**

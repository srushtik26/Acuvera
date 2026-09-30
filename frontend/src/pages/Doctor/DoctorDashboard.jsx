import { useState, useEffect, useCallback, useRef } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Shell from "../../components/Shell";
import {
    EncounterAPI,
    TriageAPI,
    AllocationAPI,
    EscalationAPI,
    AssessmentAPI,
    AdminAPI,
    InsightAPI,
} from "../../api/client";
import {
    Stethoscope,
    CheckCircle,
    AlertTriangle,
    Repeat,
    XCircle,
    Heart,
    Activity,
    Brain,
    Target,
    Clock,
    MapPin,
    ClipboardList,
    History,
    LayoutDashboard,
    ChevronRight,
    Info,
    RefreshCw,
    User,
    FileText,
    AlertCircle,
    Zap,
    Shield,
    Upload,
    X,
    Check,
} from "lucide-react";
import { useAuthStore } from "../../store/authStore";

// ─── Escalation Alert Banner ─────────────────────────────────────────────
const ICU_BEDS = [
    "ICU-A1",
    "ICU-A2",
    "ICU-A3",
    "ICU-A4",
    "ICU-B1",
    "ICU-B2",
    "ICU-B3",
    "ICU-B4",
];

function EscalationAlertBanner() {
    const [alerts, setAlerts] = useState([]);
    const [elapsed, setElapsed] = useState({});
    const [encounterMeta, setEncounterMeta] = useState({});
    const tickRef = useRef();

    const loadAlerts = useCallback(async () => {
        try {
            const events = await EscalationAPI.events({});
            const dismissedAlerts = JSON.parse(
                localStorage.getItem("dismissedAlerts") || "[]",
            );
            const unacked = (Array.isArray(events) ? events : []).filter(
                (e) => !e.acknowledged_at && !dismissedAlerts.includes(e.id),
            );
            setAlerts(unacked);
            const newMeta = {};
            await Promise.all(
                unacked.map(async (ev, idx) => {
                    if (!encounterMeta[ev.encounter_id]) {
                        try {
                            const enc = await EncounterAPI.get(ev.encounter_id);
                            newMeta[ev.encounter_id] = {
                                patient_name: enc.patient_detail?.name || "Unknown Patient",
                                icu_bed:
                                    ev.type === "code_blue"
                                        ? ICU_BEDS[idx % ICU_BEDS.length]
                                        : null,
                            };
                        } catch { }
                    }
                }),
            );
            if (Object.keys(newMeta).length > 0)
                setEncounterMeta((prev) => ({ ...prev, ...newMeta }));
        } catch { }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        loadAlerts();
        const t = setInterval(loadAlerts, 15000);
        return () => clearInterval(t);
    }, [loadAlerts]);

    useEffect(() => {
        tickRef.current = setInterval(() => {
            setElapsed((prev) => {
                const next = { ...prev };
                alerts.forEach((ev) => {
                    next[ev.id] = Math.floor(
                        (Date.now() - new Date(ev.timestamp)) / 1000,
                    );
                });
                return next;
            });
        }, 1000);
        return () => clearInterval(tickRef.current);
    }, [alerts]);

    const handleDismiss = (eventId) => {
        const dismissedAlerts = JSON.parse(
            localStorage.getItem("dismissedAlerts") || "[]",
        );
        if (!dismissedAlerts.includes(eventId)) {
            localStorage.setItem(
                "dismissedAlerts",
                JSON.stringify([...dismissedAlerts, eventId]),
            );
        }
        setAlerts((prev) => prev.filter((e) => e.id !== eventId));
    };

    if (alerts.length === 0) return null;

    const typeLabel = {
        code_blue: "CODE BLUE",
        trauma_override: "TRAUMA OVERRIDE",
        manual_escalation: "ESCALATION",
    };

    return (
        <div className="mb-5 flex flex-col gap-2">
            {alerts.map((ev) => {
                const secs = elapsed[ev.id] || 0;
                const mins = Math.floor(secs / 60);
                const s = secs % 60;
                const timeStr = `${mins}:${String(s).padStart(2, "0")}`;
                const isSlaRisk = secs > 90;
                const meta = encounterMeta[ev.encounter_id] || {};
                const patientName = meta.patient_name || "Loading...";
                const icuBed = meta.icu_bed;
                return (
                    <div
                        key={ev.id}
                        className="flex items-center justify-between gap-4 rounded-xl border-2 border-rose-200 bg-rose-50/80 p-4 backdrop-blur-sm animate-pulse-border"
                        style={{ borderLeftWidth: "6px" }}
                    >
                        <div className="flex flex-1 flex-wrap items-center gap-4">
                            <span className="text-sm font-black uppercase tracking-wider text-rose-700">
                                🚨 {typeLabel[ev.type] || "ESCALATION"}
                            </span>
                            <span className="font-bold text-gray-700">{patientName}</span>
                            {icuBed && (
                                <span className="rounded-md border border-rose-200 bg-rose-100/50 px-2 py-0.5 font-mono text-xs font-black uppercase tracking-wider text-rose-700">
                                    🏥 {icuBed}
                                </span>
                            )}
                            <span
                                className={`font-mono text-sm font-bold ${isSlaRisk ? "text-rose-600" : "text-amber-600"
                                    }`}
                            >
                                ⏱ {timeStr}
                                {isSlaRisk && " — SLA AT RISK"}
                            </span>
                        </div>
                        <button
                            onClick={() => handleDismiss(ev.id)}
                            className="whitespace-nowrap rounded-lg border border-rose-200 bg-rose-100/50 px-3 py-1 text-xs font-bold text-rose-700 transition-all hover:bg-rose-200/80"
                            title="Dismiss this alert"
                        >
                            ✕ Dismiss
                        </button>
                    </div>
                );
            })}
        </div>
    );
}

// ─── Priority Badge ──────────────────────────────────────────────────────
function PriorityBadge({ priority }) {
    const colors = {
        critical: "bg-rose-100 text-rose-700 border-rose-200",
        high: "bg-orange-100 text-orange-700 border-orange-200",
        moderate: "bg-amber-100 text-amber-700 border-amber-200",
        low: "bg-emerald-100 text-emerald-700 border-emerald-200",
    };
    return (
        <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${colors[priority]}`}
        >
            {priority}
        </span>
    );
}

// ─── waitLabel helper ────────────────────────────────────────────────────
function waitLabel(createdAt, endTime) {
    const end = endTime ? new Date(endTime).getTime() : Date.now();
    const mins = Math.floor((end - new Date(createdAt)) / 60000);
    if (mins < 1) return "< 1m";
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

// ─── Reject Modal ────────────────────────────────────────────────────────
function RejectModal({ encounter, onClose, onDone }) {
    const [reason, setReason] = useState("");
    const [loading, setLoading] = useState(false);
    const REASONS = [
        "in_procedure",
        "specialty_mismatch",
        "max_caseload_reached",
        "personal_emergency",
        "outside_expertise",
        "other",
    ];

    const handleReject = async () => {
        if (!reason) return;
        setLoading(true);
        try {
            await AllocationAPI.respond({
                encounter_id: encounter.id,
                accepted: false,
                rejection_reason: reason,
            });
            onDone();
            onClose();
        } catch (err) {
            alert("Error: " + (err.response?.data?.errors || err.message));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="w-full max-w-md rounded-2xl bg-white/90 p-6 shadow-xl backdrop-blur-xl border border-white/50">
                <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-black text-gray-800">
                        ✗ Reject Assignment
                    </h3>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1 text-gray-500 hover:bg-gray-100"
                    >
                        <X size={18} />
                    </button>
                </div>
                <p className="mb-4 text-sm text-gray-600">
                    Rejecting{" "}
                    <span className="font-bold text-gray-800">
                        {encounter.patient_detail?.name}
                    </span>
                    . Select reason:
                </p>
                <div className="mb-4 flex flex-col gap-1">
                    {REASONS.map((r) => (
                        <button
                            key={r}
                            onClick={() => setReason(r)}
                            className={`rounded-lg px-4 py-2 text-left text-sm font-medium capitalize transition-all ${reason === r
                                ? "bg-rose-600 text-white"
                                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                }`}
                        >
                            {r.replace(/_/g, " ")}
                        </button>
                    ))}
                </div>
                <div className="flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleReject}
                        disabled={loading || !reason}
                        className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                    >
                        {loading ? "Rejecting..." : "Confirm Reject"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Escalate Modal ──────────────────────────────────────────────────────
function EscalateModal({ encounter, onClose, onDone }) {
    const [type, setType] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const TYPES = [
        {
            value: "code_blue",
            label: "🔵 Code Blue",
            desc: "Cardiac/respiratory arrest — immediate response",
            color: "rose",
        },
        {
            value: "trauma_override",
            label: "🚨 Trauma Override",
            desc: "Severe trauma requiring immediate team",
            color: "orange",
        },
        {
            value: "manual_escalation",
            label: "⚠️ Manual Escalation",
            desc: "Urgent clinical concern",
            color: "amber",
        },
    ];

    const handleEscalate = async () => {
        if (!type) {
            setError("Select escalation type");
            return;
        }
        setLoading(true);
        try {
            await EscalationAPI.trigger({ encounter_id: encounter.id, type });
            onDone();
            onClose();
        } catch (err) {
            setError(err.response?.data?.errors || err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="w-full max-w-md rounded-2xl bg-white/90 p-6 shadow-xl backdrop-blur-xl border border-white/50">
                <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-black text-gray-800">
                        🚨 Trigger Escalation
                    </h3>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1 text-gray-500 hover:bg-gray-100"
                    >
                        <X size={18} />
                    </button>
                </div>
                <p className="mb-4 text-sm text-gray-600">
                    Patient:{" "}
                    <span className="font-bold text-gray-800">
                        {encounter.patient_detail?.name}
                    </span>
                    <PriorityBadge priority={encounter.priority} />
                </p>
                <div className="mb-4 flex flex-col gap-2">
                    {TYPES.map((t) => (
                        <button
                            key={t.value}
                            onClick={() => setType(t.value)}
                            className={`flex flex-col items-start rounded-lg border-2 p-3 text-left transition-all ${type === t.value
                                ? `border-${t.color}-500 bg-${t.color}-50`
                                : "border-gray-200 bg-gray-50 hover:border-gray-300"
                                }`}
                        >
                            <span
                                className={`font-bold ${type === t.value ? `text-${t.color}-700` : "text-gray-700"}`}
                            >
                                {t.label}
                            </span>
                            <span className="text-xs text-gray-500">{t.desc}</span>
                        </button>
                    ))}
                </div>
                {error && <div className="mb-3 text-sm text-rose-600">⚠ {error}</div>}
                <div className="flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleEscalate}
                        disabled={loading || !type}
                        className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                    >
                        {loading ? "Escalating..." : "🚨 Confirm Escalation"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Refer Modal ─────────────────────────────────────────────────────────
function ReferModal({ encounter, currentUserId, onClose, onDone }) {
    const [suggestion, setSuggestion] = useState(null);
    const [doctors, setDoctors] = useState([]);
    const [selectedDoc, setSelectedDoc] = useState("");
    const [loading, setLoading] = useState(false);
    const [suggesting, setSuggesting] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        Promise.all([
            AllocationAPI.suggest(encounter.id).catch(() => null),
            AdminAPI.doctors(encounter.department).catch(() => []),
        ]).then(([sug, docs]) => {
            setSuggestion(sug);
            const filtered = (Array.isArray(docs) ? docs : []).filter(
                (d) => String(d.id) !== String(currentUserId),
            );
            setDoctors(filtered);
            if (sug?.doctor_id && String(sug.doctor_id) !== String(currentUserId)) {
                setSelectedDoc(sug.doctor_id);
            }
            setSuggesting(false);
        });
    }, [encounter.id, encounter.department, currentUserId]);

    const handleRefer = async () => {
        if (!selectedDoc) {
            setError("Select a doctor");
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await AllocationAPI.refer({
                encounter_id: encounter.id,
                to_doctor_id: selectedDoc,
            });
            onDone();
            onClose();
        } catch (err) {
            setError(err.response?.data?.errors || err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="w-full max-w-md rounded-2xl bg-white/90 p-6 shadow-xl backdrop-blur-xl border border-white/50">
                <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-black text-gray-800">🔄 Refer Patient</h3>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1 text-gray-500 hover:bg-gray-100"
                    >
                        <X size={18} />
                    </button>
                </div>
                <p className="mb-4 text-sm text-gray-600">
                    Transfer{" "}
                    <span className="font-bold text-gray-800">
                        {encounter.patient_detail?.name}
                    </span>{" "}
                    to another doctor in this department.
                </p>
                {suggesting ? (
                    <div className="flex h-20 items-center justify-center">
                        <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                    </div>
                ) : (
                    <>
                        {suggestion?.success &&
                            String(suggestion.doctor_id) !== String(currentUserId) && (
                                <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm">
                                    <div className="mb-1 flex items-center gap-1 font-bold text-blue-700">
                                        <Zap size={14} /> AI Suggestion
                                    </div>
                                    <span className="font-semibold text-gray-800">
                                        {suggestion.doctor_name}
                                    </span>
                                    <span className="ml-2 text-gray-600">
                                        Workload: {suggestion.workload_score} ·{" "}
                                        {suggestion.availability_state}
                                    </span>
                                </div>
                            )}
                        {doctors.length === 0 ? (
                            <div className="mb-4 text-amber-600">
                                ⚠ No other available doctors in this department.
                            </div>
                        ) : (
                            <div className="mb-4">
                                <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-gray-500">
                                    Select Doctor
                                </label>
                                <select
                                    value={selectedDoc}
                                    onChange={(e) => setSelectedDoc(e.target.value)}
                                    className="w-full rounded-lg border border-gray-300 bg-white/80 p-2 text-gray-700 backdrop-blur-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                                >
                                    <option value="">— Choose doctor —</option>
                                    {doctors.map((d) => (
                                        <option key={d.id} value={d.id}>
                                            {d.full_name}
                                            {suggestion?.doctor_id === d.id
                                                ? " ⭐ Suggested"
                                                : ""} — {d.availability_state}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </>
                )}
                {error && <div className="mb-3 text-sm text-rose-600">⚠ {error}</div>}
                <div className="flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleRefer}
                        disabled={loading || suggesting || !selectedDoc}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                    >
                        {loading ? "Referring..." : "🔄 Confirm Referral"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── AI Insight Panel ────────────────────────────────────────────────────
function AiInsightPanel({ encounterId, vitals = {} }) {
    const [insight, setInsight] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const generate = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await InsightAPI.generate(encounterId);
            setInsight(data);
        } catch (e) {
            setError("AI insight unavailable — using clinical judgment");
        } finally {
            setLoading(false);
        }
    };

    const confColor = (c) => {
        if (c === "high")
            return "text-emerald-600 bg-emerald-50 border-emerald-200";
        if (c === "medium") return "text-amber-600 bg-amber-50 border-amber-200";
        return "text-gray-500 bg-gray-50 border-gray-200";
    };

    const buildVitalsExplainability = (v) => {
        if (!v || Object.keys(v).length === 0) return [];
        const explanations = [];

        const hr = v.hr || v.heart_rate;
        const spo2 = v.spo2 || v.oxygen_saturation;
        const sbp = v.bp_systolic || v.systolic_bp;
        const dbp = v.bp_diastolic || v.diastolic_bp;
        const temp = v.temp || v.temperature;
        const gcs = v.gcs;
        const rr = v.rr || v.respiratory_rate;
        const pain = v.pain_score;

        if (hr) {
            if (hr > 140)
                explanations.push({
                    vital: "HR",
                    value: `${hr} bpm`,
                    threshold: ">140 = severe tachycardia",
                    flag: "🔴",
                    reason: `Heart rate of ${hr} bpm is critically high (threshold >140 bpm). Severe tachycardia suggests haemodynamic instability — likely cause is acute blood loss, septic shock, or severe cardiac compromise.`,
                });
            else if (hr > 100)
                explanations.push({
                    vital: "HR",
                    value: `${hr} bpm`,
                    threshold: ">100 = tachycardia",
                    flag: "🟠",
                    reason: `Heart rate of ${hr} bpm indicates tachycardia (normal: 60–100 bpm). This points toward acute stress, pain, fever, dehydration, or early cardiovascular decompensation.`,
                });
            else if (hr < 50)
                explanations.push({
                    vital: "HR",
                    value: `${hr} bpm`,
                    threshold: "<50 = bradycardia",
                    flag: "🟡",
                    reason: `Heart rate of ${hr} bpm is bradycardic (normal: 60–100 bpm). Consider heart block, beta-blocker toxicity, or vagal overstimulation.`,
                });
        }

        if (sbp) {
            if (sbp < 90)
                explanations.push({
                    vital: "BP Systolic",
                    value: `${sbp} mmHg`,
                    threshold: "<90 = hypotension/shock",
                    flag: "🔴",
                    reason: `Systolic BP of ${sbp} mmHg is below the 90 mmHg shock threshold. This indicates haemodynamic compromise — urgent consideration for septic shock, cardiogenic shock, or haemorrhage.`,
                });
            else if (sbp > 180)
                explanations.push({
                    vital: "BP Systolic",
                    value: `${sbp} mmHg`,
                    threshold: ">180 = hypertensive crisis",
                    flag: "🔴",
                    reason: `Systolic BP of ${sbp} mmHg exceeds 180 mmHg — hypertensive urgency/emergency. Elevated risk of hypertensive stroke, aortic dissection, or acute pulmonary oedema.`,
                });
            else if (sbp > 140)
                explanations.push({
                    vital: "BP Systolic",
                    value: `${sbp} mmHg`,
                    threshold: ">140 = hypertension",
                    flag: "🟡",
                    reason: `Systolic BP of ${sbp} mmHg is above the 140 mmHg hypertension threshold. In an acute setting this contributes to cardiac, renal, and neurological stress.`,
                });
        }

        if (spo2) {
            if (spo2 < 90)
                explanations.push({
                    vital: "SpO₂",
                    value: `${spo2}%`,
                    threshold: "<90% = severe hypoxemia",
                    flag: "🔴",
                    reason: `SpO₂ of ${spo2}% is critically low (normal: 95–100%). Severe hypoxemia indicates significant respiratory failure — consistent with pulmonary embolism, pneumonia, or acute pulmonary oedema.`,
                });
            else if (spo2 < 94)
                explanations.push({
                    vital: "SpO₂",
                    value: `${spo2}%`,
                    threshold: "<94% = hypoxemia",
                    flag: "🟠",
                    reason: `SpO₂ of ${spo2}% is below the 94% clinical threshold. Moderate hypoxemia raises concern for pulmonary pathology — oxygen supplementation is likely needed.`,
                });
        }

        if (temp) {
            if (temp > 38.5)
                explanations.push({
                    vital: "Temp",
                    value: `${temp}°C`,
                    threshold: ">38.5°C = fever",
                    flag: "🟠",
                    reason: `Temperature of ${temp}°C indicates significant fever (threshold >38.5°C). This points to an active infectious or inflammatory process — sepsis screening warranted if other criteria present.`,
                });
            else if (temp < 36.0)
                explanations.push({
                    vital: "Temp",
                    value: `${temp}°C`,
                    threshold: "<36°C = hypothermia",
                    flag: "🟡",
                    reason: `Temperature of ${temp}°C is below normal (36–37.5°C). Hypothermia in an acute presentation may indicate sepsis, endocrine failure, or environmental exposure.`,
                });
        }

        if (gcs) {
            if (gcs <= 8)
                explanations.push({
                    vital: "GCS",
                    value: `${gcs}/15`,
                    threshold: "≤8 = severe neurological compromise",
                    flag: "🔴",
                    reason: `GCS of ${gcs}/15 is critically low (threshold ≤8 = comatose). This indicates severe neurological depression — airway protection is an immediate priority. Causes include stroke, TBI, metabolic encephalopathy, or toxidrome.`,
                });
            else if (gcs < 13)
                explanations.push({
                    vital: "GCS",
                    value: `${gcs}/15`,
                    threshold: "<13 = moderate impairment",
                    flag: "🟠",
                    reason: `GCS of ${gcs}/15 indicates moderate neurological impairment (normal: 15). Consider altered consciousness — causes include intracranial event, hypoglycaemia, hypoxia, or medication effect.`,
                });
        }

        if (rr) {
            if (rr > 25)
                explanations.push({
                    vital: "RR",
                    value: `${rr} /min`,
                    threshold: ">25 = tachypnoea",
                    flag: "🟠",
                    reason: `Respiratory rate of ${rr}/min is elevated (normal: 12–20/min). Significant tachypnoea indicates respiratory distress — consider pneumonia, PE, metabolic acidosis, or cardiac failure.`,
                });
            else if (rr < 10)
                explanations.push({
                    vital: "RR",
                    value: `${rr} /min`,
                    threshold: "<10 = bradypnoea",
                    flag: "🟡",
                    reason: `Respiratory rate of ${rr}/min is below normal. Bradypnoea suggests CNS depression, opiate toxicity, or severe metabolic derangement.`,
                });
        }

        if (pain && pain >= 7) {
            explanations.push({
                vital: "Pain Score",
                value: `${pain}/10`,
                threshold: "≥7 = severe pain",
                flag: "🟠",
                reason: `Pain score of ${pain}/10 indicates severe pain (threshold ≥7). Severe pain in the acute setting warrants urgent analgesia and investigation — consistent with ACS, aortic dissection, or obstructive pathology.`,
            });
        }

        return explanations;
    };

    return (
        <div className="mb-5 animate-in fade-in zoom-in-95 duration-200 rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-5 py-3">
                <span className="text-sm font-black tracking-wider text-slate-800">
                    🧠 AI Clinical Insight
                </span>
                <div className="flex items-center gap-3">
                    {insight?.cached && (
                        <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 bg-emerald-100 px-2 py-1 rounded-full">
                            ✓ Cached
                        </span>
                    )}
                    <button
                        onClick={generate}
                        disabled={loading}
                        className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-indigo-700 hover:shadow disabled:opacity-50"
                    >
                        {loading
                            ? "⏳ Generating..."
                            : insight
                                ? "↻ Refresh"
                                : "✦ Generate Insight"}
                    </button>
                </div>
            </div>

            {error && <div className="p-3 text-xs text-rose-600">⚠ {error}</div>}

            {insight && !error && (
                <div className="p-5">
                    {/* Differentials */}
                    <div className="mb-4">
                        <div className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-gray-500">
                            <span className="h-3 w-0.5 rounded-full bg-indigo-400" />
                            Differential Diagnoses
                        </div>
                        <div className="space-y-2">
                            {(insight.differentials || []).map((d, i) => (
                                <div
                                    key={i}
                                    className={`rounded-xl border p-4 shadow-sm transition-all hover:shadow-md ${confColor(d.confidence)}`}
                                >
                                    <div className="flex items-center gap-3">
                                        <span
                                            className={`h-3 w-3 rounded-full ${confColor(d.confidence).split(" ")[0].replace("text", "bg")}`}
                                        />
                                        <span className="text-base font-bold text-slate-800">
                                            {d.condition}
                                        </span>
                                        <span
                                            className={`ml-auto rounded-full border px-2.5 py-0.5 text-[10px] font-black uppercase tracking-widest ${confColor(d.confidence)}`}
                                        >
                                            {d.confidence}
                                        </span>
                                    </div>
                                    {d.reason && (
                                        <p className="mt-2 text-xs leading-relaxed text-slate-600">{d.reason}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Investigations */}
                    <div className="mb-4">
                        <div className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-gray-500">
                            <span className="h-3 w-0.5 rounded-full bg-blue-400" />
                            Suggested Investigations
                        </div>
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {(insight.investigations || []).map((inv, i) => {
                                const name = typeof inv === "string" ? inv : inv?.name;
                                const reason = typeof inv === "object" ? inv?.reason : null;
                                return (
                                    <div
                                        key={i}
                                        className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                                    >
                                        <div className="flex items-start gap-2">
                                            <span className="text-xs font-black text-indigo-600">
                                                {i + 1}.
                                            </span>
                                            <span className="text-sm font-bold text-slate-800">
                                                {name}
                                            </span>
                                        </div>
                                        {reason && (
                                            <p className="mt-2 text-xs leading-relaxed text-slate-600">{reason}</p>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Vitals-Based Explainability */}
                    {buildVitalsExplainability(vitals).length > 0 && (
                        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div className="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-purple-700">
                                <span className="h-4 w-1 rounded-full bg-purple-500" />
                                Vital-Sign Threshold Analysis
                            </div>
                            <div className="space-y-3">
                                {buildVitalsExplainability(vitals).map((e, i) => (
                                    <div
                                        key={i}
                                        className="rounded-lg border border-slate-100 bg-slate-50 p-3"
                                    >
                                        <div className="flex items-center gap-2 text-xs">
                                            <span className="text-sm">{e.flag}</span>
                                            <span className="font-bold text-slate-800">
                                                {e.vital}
                                            </span>
                                            <span className="rounded-md bg-white px-2 py-1 font-mono text-[11px] font-bold text-purple-700 shadow-sm border border-slate-100">
                                                {e.value}
                                            </span>
                                            <span className="ml-auto text-[10px] font-bold text-purple-600">
                                                {e.threshold}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-xs leading-relaxed text-slate-600">{e.reason}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Risk Signals */}
                    {(insight.risk_signals ||
                        (insight.differentials || []).filter((d) => d.confidence === "high")
                            .length > 0) && (
                            <div className="mb-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                                <div className="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-amber-700">
                                    <span className="h-4 w-1 rounded-full bg-amber-500" />
                                    Key Clinical Flags
                                </div>
                                <div className="space-y-2 text-xs text-slate-800">
                                    {insight.risk_signals?.slice(0, 4).map((sig, i) => (
                                        <div key={i} className="flex gap-2 leading-relaxed">
                                            <span className="text-amber-500 font-black">▸</span> {sig}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                    {/* Possible Outcomes */}
                    {(insight.possible_outcomes || insight.outcomes) && (
                        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div className="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-rose-700">
                                <span className="h-4 w-1 rounded-full bg-rose-500" />
                                Possible Outcomes if Untreated
                            </div>
                            <div className="space-y-2 text-xs text-slate-800">
                                {(insight.possible_outcomes || insight.outcomes || []).map(
                                    (o, i) => (
                                        <div key={i} className="flex gap-2 leading-relaxed">
                                            <span className="text-rose-500 font-black">⚠</span>{" "}
                                            {typeof o === "string" ? o : o?.outcome}
                                        </div>
                                    ),
                                )}
                            </div>
                        </div>
                    )}

                    {/* Risk Prediction Section (Optional if insight provides it, or from triage) */}
                    {insight.risk_prediction && (
                        <div className="mb-4">
                            <div className="mb-2 flex items-center justify-between">
                                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-rose-700">
                                    <span className="h-3 w-0.5 rounded-full bg-rose-500" />
                                    Clinical Deterioration Prediction
                                </div>
                                {insight.risk_prediction.prediction_generated_at && (
                                    <span className="text-[9px] text-gray-500">
                                        🕒 {new Date(insight.risk_prediction.prediction_generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                )}
                            </div>

                            <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-3 shadow-sm">
                                {/* Overall Risk Row */}
                                <div className="mb-3 flex items-center justify-between border-b border-dashed border-slate-200 pb-2">
                                    <span className="text-xs font-semibold text-slate-700">Overall Deterioration Risk</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-base font-bold text-slate-900">
                                            {insight.risk_prediction.overall_deterioration_risk}%
                                        </span>
                                        <span className={`rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-wider shadow-sm ${insight.risk_prediction.risk_level === 'CRITICAL' ? 'bg-rose-100 text-rose-700 border border-rose-200' :
                                            insight.risk_prediction.risk_level === 'HIGH' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                                                insight.risk_prediction.risk_level === 'MODERATE' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                                                    'bg-emerald-100 text-emerald-700 border border-emerald-200'
                                            }`}>
                                            {insight.risk_prediction.risk_level}
                                        </span>
                                    </div>
                                </div>

                                {/* Risk Breakdown */}
                                <div className="grid grid-cols-3 gap-2">
                                    <div className="flex flex-col items-center rounded-lg border border-slate-100 bg-white p-2 shadow-sm">
                                        <span className="text-[9px] font-black uppercase tracking-wider text-slate-500">ICU Admit</span>
                                        <span className="mt-1 text-sm font-bold text-slate-800">{insight.risk_prediction.icu_probability}%</span>
                                    </div>
                                    <div className="flex flex-col items-center rounded-lg border border-slate-100 bg-white p-2 shadow-sm">
                                        <span className="text-[9px] font-black uppercase tracking-wider text-slate-500">Resp Failure</span>
                                        <span className="mt-1 text-sm font-bold text-slate-800">{insight.risk_prediction.respiratory_failure_risk}%</span>
                                    </div>
                                    <div className="flex flex-col items-center rounded-lg border border-slate-100 bg-white p-2 shadow-sm">
                                        <span className="text-[9px] font-black uppercase tracking-wider text-slate-500">Cardiac Event</span>
                                        <span className="mt-1 text-sm font-bold text-slate-800">{insight.risk_prediction.cardiac_event_risk}%</span>
                                    </div>
                                </div>

                                {/* Top Drivers */}
                                {insight.risk_prediction.top_risk_drivers?.length > 0 && (
                                    <div className="mt-3 border-t border-dashed border-slate-200 pt-2">
                                        <div className="mb-2 text-[9px] font-black uppercase tracking-wider text-slate-500">Top Risk Drivers</div>
                                        <div className="space-y-1.5">
                                            {insight.risk_prediction.top_risk_drivers.map((drv, idx) => (
                                                <div key={idx} className="flex items-center justify-between text-[10px]">
                                                    <span className="text-slate-600">{drv.label}</span>
                                                    <div className="flex items-center gap-1.5">
                                                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
                                                            <div className="h-full bg-rose-500" style={{ width: `${drv.impact_percentage}%` }} />
                                                        </div>
                                                        <span className="min-w-[28px] text-right font-bold text-rose-600">+{drv.impact_percentage}%</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {insight?.disclaimer && (
                <div className="border-t border-slate-100 bg-slate-50 p-4 text-center text-[10px] text-slate-500 rounded-b-xl">
                    {insight.disclaimer}
                </div>
            )}
        </div>
    );
}

// ─── Assessment Modal ────────────────────────────────────────────────────
function AssessmentModal({ encounter, onClose, onDone }) {
    const [notes, setNotes] = useState("");
    const [media, setMedia] = useState([]); // [{name, mime_type, data_b64, preview}]
    const [saving, setSaving] = useState(false);
    const [completing, setCompleting] = useState(false);
    const [report, setReport] = useState(null);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('insight');
    const fileRef = useRef();

    // Load existing assessment
    useEffect(() => {
        AssessmentAPI.get(encounter.id)
            .then((data) => {
                if (data) {
                    setNotes(data.notes || "");
                    setMedia(
                        (data.media_json || []).map((m) => ({
                            ...m,
                            preview: `data:${m.mime_type};base64,${m.data_b64}`,
                        })),
                    );
                    if (data.report_text) setReport(data.report_text);
                }
            })
            .catch(() => { });
    }, [encounter.id]);

    const handleFileAdd = (e) => {
        const files = Array.from(e.target.files);
        files.forEach((file) => {
            const reader = new FileReader();
            reader.onload = (ev) => {
                const dataUrl = ev.target.result;
                const b64 = dataUrl.split(",")[1];
                setMedia((prev) => [
                    ...prev,
                    {
                        name: file.name,
                        mime_type: file.type,
                        data_b64: b64,
                        preview: dataUrl,
                    },
                ]);
            };
            reader.readAsDataURL(file);
        });
        e.target.value = "";
    };

    const removeMedia = (idx) =>
        setMedia((prev) => prev.filter((_, i) => i !== idx));

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const newMedia = media
                .filter((m) => !m._saved)
                .map(({ name, mime_type, data_b64 }) => ({
                    name,
                    mime_type,
                    data_b64,
                }));
            await AssessmentAPI.save(encounter.id, { notes, media: newMedia });
            setMedia((prev) => prev.map((m) => ({ ...m, _saved: true })));
        } catch (err) {
            setError(err.response?.data?.errors || err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleComplete = async () => {
        setCompleting(true);
        setError(null);
        try {
            const newMedia = media
                .filter((m) => !m._saved)
                .map(({ name, mime_type, data_b64 }) => ({
                    name,
                    mime_type,
                    data_b64,
                }));
            if (newMedia.length > 0) {
                await AssessmentAPI.save(encounter.id, { notes, media: newMedia });
            }
            const result = await AssessmentAPI.complete(encounter.id, { notes });
            setReport(result.report_text || "Assessment completed.");
            setTimeout(() => {
                onDone();
            }, 2000);
        } catch (err) {
            setError(err.response?.data?.errors || err.message);
        } finally {
            setCompleting(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white/90 p-6 shadow-xl backdrop-blur-xl border border-white/50">
                <div className="sticky top-0 z-10 mb-4 flex items-center justify-between bg-white/80 pb-2 backdrop-blur-sm">
                    <h3 className="text-lg font-black text-gray-800">
                        🩺 Assessment — {encounter.patient_detail?.name}
                    </h3>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1 text-gray-500 hover:bg-gray-100"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Patient summary */}
                <div className="mb-4 flex flex-wrap gap-4 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                    <PriorityBadge priority={encounter.priority} />
                    <span>
                        Score:{" "}
                        <span className="font-bold text-gray-800">
                            {encounter.risk_score}
                        </span>
                    </span>
                    <span>
                        Wait:{" "}
                        <span className="font-bold text-gray-800">
                            {waitLabel(encounter.created_at)}
                        </span>
                    </span>
                    {encounter.triage_data?.vitals_json &&
                        Object.entries(encounter.triage_data.vitals_json)
                            .filter(([, v]) => v != null)
                            .slice(0, 4)
                            .map(([k, v]) => (
                                <span key={k}>
                                    {k}: <span className="font-bold text-gray-800">{v}</span>
                                </span>
                            ))}
                </div>

                {report ? (
                    <>
                        <div className="mb-3 text-sm font-bold text-emerald-600">
                            ✅ Assessment Complete — AI Report Generated
                        </div>
                        <div className="whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm text-gray-800">
                            {report}
                        </div>
                        <div className="mt-4 flex justify-end">
                            <button
                                onClick={onClose}
                                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
                            >
                                Close
                            </button>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="mb-5 flex gap-2 border-b-2 border-slate-100 pb-2">
                            <button
                                onClick={() => setActiveTab('insight')}
                                className={`px-5 py-2.5 text-xs font-black uppercase tracking-wider transition-all rounded-lg ${activeTab === 'insight' ? 'text-indigo-700 bg-white shadow-sm border border-slate-200' : 'text-slate-500 hover:text-indigo-600 hover:bg-white/50 border border-transparent'}`}
                            >
                                AI Clinical Insight
                            </button>
                            <button
                                onClick={() => setActiveTab('notes')}
                                className={`px-5 py-2.5 text-xs font-black uppercase tracking-wider transition-all rounded-lg ${activeTab === 'notes' ? 'text-indigo-700 bg-white shadow-sm border border-slate-200' : 'text-slate-500 hover:text-indigo-600 hover:bg-white/50 border border-transparent'}`}
                            >
                                Assessment Notes
                            </button>
                        </div>

                        {activeTab === 'insight' ? (
                            <AiInsightPanel
                                encounterId={encounter.id}
                                vitals={encounter.triage_data?.vitals_json || {}}
                            />
                        ) : (
                            <div className="animate-in fade-in zoom-in-95 duration-200">
                                {/* Notes */}
                                <div className="mb-4">
                                    <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-gray-500">
                                        CLINICAL NOTES
                                    </label>
                                    <textarea
                                        rows={6}
                                        className="w-full resize-y rounded-lg border border-gray-300 bg-white/80 p-3 text-sm text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                                        placeholder="Enter clinical observations, examination findings, differential diagnosis, treatment plan..."
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                    />
                                </div>

                                {/* Media */}
                                <div className="mb-4">
                                    <div className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-500">
                                        ATTACHMENTS (Photos / Documents)
                                    </div>
                                    <input
                                        ref={fileRef}
                                        type="file"
                                        accept="image/*,application/pdf"
                                        multiple
                                        className="hidden"
                                        onChange={handleFileAdd}
                                    />
                                    <button
                                        onClick={() => fileRef.current.click()}
                                        className="mb-2 flex items-center gap-1 rounded-lg border border-gray-300 bg-white/80 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100"
                                    >
                                        <Upload size={14} /> Add Photo / File
                                    </button>
                                    {media.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {media.map((m, i) => (
                                                <div key={i} className="relative">
                                                    {m.mime_type?.startsWith("image/") ? (
                                                        <img
                                                            src={m.preview}
                                                            alt={m.name}
                                                            className="h-20 w-20 rounded-lg border border-gray-300 object-cover"
                                                        />
                                                    ) : (
                                                        <div className="flex h-20 w-20 items-center justify-center rounded-lg border border-gray-300 bg-gray-100 p-2 text-center text-[10px] text-gray-600">
                                                            📄 {m.name}
                                                        </div>
                                                    )}
                                                    {!m._saved && (
                                                        <button
                                                            onClick={() => removeMedia(i)}
                                                            className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-xs text-white shadow"
                                                        >
                                                            ✕
                                                        </button>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-600">
                                ⚠ {error}
                            </div>
                        )}

                        <div className="mt-2 flex justify-end gap-3 border-t border-gray-200 pt-4">
                            <button
                                onClick={onClose}
                                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
                            >
                                Close
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="rounded-lg bg-gray-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                            >
                                {saving ? "Saving..." : "💾 Save Notes"}
                            </button>
                            <button
                                onClick={handleComplete}
                                disabled={completing || !notes.trim()}
                                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                            >
                                {completing ? (
                                    <span className="flex items-center gap-1">
                                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        Generating...
                                    </span>
                                ) : (
                                    "✅ Complete Assessment"
                                )}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

// ─── My Cases Page ───────────────────────────────────────────────────────
function MyCasesPage() {
    const { user } = useAuthStore();
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(true);
    const [rejectEnc, setRejectEnc] = useState(null);
    const [referEnc, setReferEnc] = useState(null);
    const [assessEnc, setAssessEnc] = useState(null);

    const load = useCallback(async () => {
        try {
            const mine = await EncounterAPI.list({
                status: "",
                assigned_doctor: user?.id,
            }).then((all) =>
                Array.isArray(all)
                    ? all.filter(
                        (e) =>
                            e.assigned_doctor === user?.id &&
                            ["in_progress", "escalated"].includes(e.status) &&
                            !e.assessment_completed,
                    )
                    : [],
            );
            setCases(mine);
        } catch {
            setCases([]);
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        load();
        const t = setInterval(load, 30000);
        return () => clearInterval(t);
    }, [load]);

    if (loading)
        return (
            <div className="flex h-64 flex-col items-center justify-center gap-4 text-gray-500">
                <div className="relative">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
                </div>
                <span className="text-sm font-medium uppercase tracking-widest">
                    Loading cases...
                </span>
            </div>
        );

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <EscalationAlertBanner />
            <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black tracking-tight text-gray-900">
                        <LayoutDashboard className="h-8 w-8 text-blue-600" /> My Cases
                    </h1>
                    <p className="mt-1 text-sm text-gray-500">
                        {cases.length} accepted cases in progress
                    </p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white/70 px-4 py-2 text-sm font-semibold text-gray-700 backdrop-blur-sm transition-all hover:bg-white/80"
                >
                    <RefreshCw size={16} className="text-blue-500" /> Refresh List
                </button>
            </div>

            {cases.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-gray-50/50 py-20 backdrop-blur-sm">
                    <div className="mb-4 text-5xl opacity-20">🏥</div>
                    <p className="font-medium text-gray-500">
                        No active cases — check <strong>Assignments</strong> for new cases
                        to accept
                    </p>
                    <button
                        onClick={load}
                        className="mt-4 text-sm text-blue-600 hover:underline"
                    >
                        Reload Dashboard
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-6">
                    {cases.map((enc) => (
                        <div
                            key={enc.id}
                            className={`group relative rounded-3xl border border-white/50 bg-white/70 p-6 shadow-xl backdrop-blur-xl transition-all hover:border-blue-200 hover:bg-white/80 ${enc.status === "escalated"
                                ? "ring-2 ring-rose-500/50 ring-offset-2 ring-offset-white"
                                : ""
                                }`}
                        >
                            <div className="flex flex-col gap-8 lg:flex-row">
                                {/* Left Section: Patient Info & Vitals */}
                                <div className="flex-1">
                                    <div className="mb-6 flex items-start justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 text-xl shadow-inner">
                                                <User className="h-6 w-6 text-blue-600" />
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-bold tracking-tight text-gray-800 group-hover:text-blue-600 transition-colors">
                                                    {enc.patient_detail?.name || "Unknown Patient"}
                                                </h3>
                                                <div className="mt-1 flex items-center gap-3">
                                                    <PriorityBadge priority={enc.priority} />
                                                    <span className="rounded-md border border-gray-200 bg-gray-100/50 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-gray-600">
                                                        {enc.status.replace("_", " ")}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        {enc.floor && (
                                            <div className="hidden items-center gap-2 rounded-xl border border-blue-200 bg-blue-50/50 px-3 py-1.5 text-xs font-bold text-blue-700 sm:flex">
                                                <MapPin size={12} />F {enc.floor} · R{" "}
                                                {enc.room_number || "?"} · B {enc.bed_number || "?"}
                                            </div>
                                        )}
                                    </div>

                                    {/* Stats Row */}
                                    <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
                                        <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white/60 px-3 py-2">
                                            <Clock size={14} className="text-gray-500" />
                                            <div>
                                                <div className="text-[10px] font-bold uppercase tracking-tighter text-gray-500">
                                                    WAIT
                                                </div>
                                                <div className="text-sm font-bold text-gray-700">
                                                    {waitLabel(enc.created_at)}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white/60 px-3 py-2">
                                            <Activity size={14} className="text-amber-600" />
                                            <div>
                                                <div className="text-[10px] font-bold uppercase tracking-tighter text-gray-500">
                                                    SCORE
                                                </div>
                                                <div className="text-sm font-bold text-gray-700">
                                                    {enc.risk_score}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white/60 px-3 py-2">
                                            <Target size={14} className="text-emerald-600" />
                                            <div>
                                                <div className="text-[10px] font-bold uppercase tracking-tighter text-gray-500">
                                                    CONF
                                                </div>
                                                <div className="text-sm font-bold text-gray-700">
                                                    {enc.confidence_score ?? "—"}%
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50/60 px-3 py-2">
                                            <Info size={14} className="text-rose-600" />
                                            <div>
                                                <div className="text-[10px] font-bold uppercase tracking-tighter text-rose-600">
                                                    REJECTS
                                                </div>
                                                <div className="text-sm font-bold text-rose-700">
                                                    {enc.rejection_count}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Detailed Vitals Bar */}
                                    {enc.triage_data?.vitals_json && (
                                        <div className="grid grid-cols-2 gap-2 rounded-2xl border border-gray-200 bg-gray-50/80 p-3 sm:grid-cols-3 md:grid-cols-6">
                                            {[
                                                {
                                                    k: "HR",
                                                    v: enc.triage_data.vitals_json.hr,
                                                    icon: <Heart size={10} />,
                                                    color: "text-rose-600",
                                                },
                                                {
                                                    k: "BP",
                                                    v: `${enc.triage_data.vitals_json.bp_systolic}/${enc.triage_data.vitals_json.bp_diastolic}`,
                                                    icon: <Activity size={10} />,
                                                    color: "text-blue-600",
                                                },
                                                {
                                                    k: "O2",
                                                    v: enc.triage_data.vitals_json.spo2,
                                                    icon: <Activity className="rotate-90" size={10} />,
                                                    color: "text-emerald-600",
                                                },
                                                {
                                                    k: "T",
                                                    v: enc.triage_data.vitals_json.temp,
                                                    icon: <Activity size={10} />,
                                                    color: "text-amber-600",
                                                },
                                                {
                                                    k: "GCS",
                                                    v: enc.triage_data.vitals_json.gcs,
                                                    icon: <Brain size={10} />,
                                                    color: "text-indigo-600",
                                                },
                                                {
                                                    k: "Pain",
                                                    v: enc.triage_data.vitals_json.pain_score,
                                                    icon: <Info size={10} />,
                                                    color: "text-gray-600",
                                                },
                                            ]
                                                .filter(
                                                    (stat) =>
                                                        stat.v != null && stat.v !== "undefined/undefined",
                                                )
                                                .map((stat) => (
                                                    <div
                                                        key={stat.k}
                                                        className="flex items-center gap-2 rounded-lg bg-white/80 px-2 py-1"
                                                    >
                                                        <span className={stat.color}>{stat.icon}</span>
                                                        <span className="text-[10px] font-black text-gray-500">
                                                            {stat.k}
                                                        </span>
                                                        <span className="text-[11px] font-bold text-gray-700">
                                                            {stat.v}
                                                        </span>
                                                    </div>
                                                ))}
                                        </div>
                                    )}
                                </div>

                                {/* Right Section: Actions */}
                                <div className="flex min-w-[160px] flex-col justify-center gap-2 lg:border-l lg:border-gray-200 lg:pl-8">
                                    <div className="mb-2">
                                        {enc.has_assessment && enc.assessment_completed && (
                                            <div className="flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-700">
                                                <CheckCircle size={12} /> ASSESSED
                                            </div>
                                        )}
                                        {enc.has_assessment && !enc.assessment_completed && (
                                            <div className="flex animate-pulse items-center justify-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-amber-700">
                                                <Stethoscope size={12} /> ASSESSING...
                                            </div>
                                        )}
                                    </div>

                                    {(enc.status === "in_progress" ||
                                        enc.status === "escalated") && (
                                            <button
                                                onClick={() => setAssessEnc(enc)}
                                                className="btn-primary w-full rounded-xl bg-blue-600 py-3 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition-all active:scale-95"
                                            >
                                                <Stethoscope size={16} className="inline mr-1" /> Patient
                                                Assessment
                                            </button>
                                        )}

                                    <div className="mt-2 grid grid-cols-2 gap-2">
                                        <button
                                            onClick={async () => {
                                                const ok = window.confirm(
                                                    `Send escalation alert for ${enc.patient_detail?.name || "this patient"}?\n\nThis will notify the response team.`,
                                                );
                                                if (!ok) return;
                                                try {
                                                    await EscalationAPI.trigger({
                                                        encounter_id: enc.id,
                                                        type: "manual_escalation",
                                                    });
                                                    load();
                                                } catch (err) {
                                                    alert(
                                                        "Error: " +
                                                        (err.response?.data?.errors || err.message),
                                                    );
                                                }
                                            }}
                                            className="rounded-xl bg-amber-100 py-2.5 text-xs font-semibold text-amber-700 transition-all hover:bg-amber-200"
                                        >
                                            <AlertTriangle size={14} className="inline mr-1" /> ALERT
                                        </button>
                                        <button
                                            onClick={() => setReferEnc(enc)}
                                            className="rounded-xl bg-gray-100 py-2.5 text-xs font-semibold text-gray-700 transition-all hover:bg-gray-200"
                                        >
                                            <Repeat size={14} className="inline mr-1" /> REFER
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {rejectEnc && (
                <RejectModal
                    encounter={rejectEnc}
                    onClose={() => setRejectEnc(null)}
                    onDone={load}
                />
            )}
            {referEnc && (
                <ReferModal
                    encounter={referEnc}
                    currentUserId={user?.id}
                    onClose={() => setReferEnc(null)}
                    onDone={load}
                />
            )}
            {assessEnc && (
                <AssessmentModal
                    encounter={assessEnc}
                    onClose={() => setAssessEnc(null)}
                    onDone={() => {
                        setAssessEnc(null);
                        load();
                    }}
                />
            )}
        </div>
    );
}

// ─── FormattedReport Component (for history) ─────────────────────────────
const FormattedReport = ({ text }) => {
    if (!text) return "No automated report available.";
    const lines = text.split("\n");
    const elements = [];

    let skipSection = false;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Skip redundant CLINICAL ASSESSMENT block on older saved fallback reports
        if (line === "CLINICAL ASSESSMENT") {
            skipSection = true;
            continue;
        }
        if (skipSection) {
            if (/^[-=]{5,}$/.test(line)) {
                continue;
            }
            if (
                line === "" &&
                i + 1 < lines.length &&
                /^[A-Z\s]+$/.test(lines[i + 1].trim()) &&
                /^[-=]{5,}$/.test(lines[i + 2]?.trim() || "")
            ) {
                skipSection = false;
            }
            if (skipSection) continue;
        }

        if (/^[-=]{5,}$/.test(line)) {
            if (elements.length > 0) {
                const prev = elements.pop();
                elements.push({
                    type: "header",
                    text: prev.text.replace(/[:-]$/, "").trim(),
                    isMain: line.includes("="),
                });
            }
        } else if (line) {
            elements.push({ type: "text", text: line });
        } else if (
            !line &&
            elements.length > 0 &&
            elements[elements.length - 1].type !== "break"
        ) {
            elements.push({ type: "break" });
        }
    }

    return (
        <div className="flex flex-col gap-1">
            {elements.map((el, i) => {
                if (el.type === "header") {
                    return (
                        <div
                            key={i}
                            className={`mt-2 border-b border-gray-200 pb-1 text-xs font-black uppercase tracking-wider ${el.isMain ? "text-gray-700" : "text-gray-500"
                                }`}
                        >
                            {el.text}
                        </div>
                    );
                } else if (el.type === "break") {
                    return <div key={i} className="h-1" />;
                }

                let content = el.text;
                if (content.includes("|") && content.includes(":")) {
                    const parts = content.split("|").map((p) => p.trim());
                    return (
                        <div key={i} className="mt-1 flex flex-wrap gap-3">
                            {parts.map((part, idx) => {
                                const [k, ...v] = part.split(":");
                                return k && v.length ? (
                                    <span
                                        key={idx}
                                        className="rounded border border-gray-200 bg-gray-50 px-2 py-1 text-xs"
                                    >
                                        <span className="font-bold text-gray-600">{k.trim()}:</span>{" "}
                                        <span className="font-semibold text-gray-800">
                                            {v.join(":").trim()}
                                        </span>
                                    </span>
                                ) : (
                                    <span key={idx} className="text-xs text-gray-600">
                                        {part}
                                    </span>
                                );
                            })}
                        </div>
                    );
                }

                return (
                    <div key={i} className="text-sm text-gray-700">
                        {content}
                    </div>
                );
            })}
        </div>
    );
};

// ─── Patient History Page ─────────────────────────────────────────────────
function PatientHistoryPage() {
    const { user } = useAuthStore();
    const [pastCases, setPastCases] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        try {
            const past = await EncounterAPI.list({
                status: "completed",
                assigned_doctor: user?.id,
            });
            setPastCases(Array.isArray(past) ? past : []);
        } catch {
            setPastCases([]);
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        load();
        const t = setInterval(load, 60000);
        return () => clearInterval(t);
    }, [load]);

    if (loading)
        return (
            <div className="flex h-64 flex-col items-center justify-center gap-4 text-gray-500">
                <div className="relative">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
                </div>
                <span className="text-sm font-medium uppercase tracking-widest">
                    Loading history...
                </span>
            </div>
        );

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <EscalationAlertBanner />
            <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black tracking-tight text-gray-900">
                        <History className="h-8 w-8 text-gray-500" /> Patient History
                    </h1>
                    <p className="mt-1 text-sm text-gray-500">
                        {pastCases.length} completed records
                    </p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white/70 px-4 py-2 text-sm font-semibold text-gray-700 backdrop-blur-sm transition-all hover:bg-white/80"
                >
                    <RefreshCw size={16} className="text-blue-500" /> Refresh
                </button>
            </div>

            {pastCases.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-gray-50/50 py-20 backdrop-blur-sm">
                    <div className="mb-4 text-5xl opacity-20">📋</div>
                    <p className="text-gray-500">
                        No completed cases in your history yet
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-6">
                    {pastCases.map((enc) => (
                        <div
                            key={enc.id}
                            className="rounded-2xl border border-gray-200 bg-white/70 p-6 shadow-lg backdrop-blur-sm"
                        >
                            {/* Header */}
                            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
                                <div className="flex items-center gap-4">
                                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-xl">
                                        <User className="h-6 w-6 text-gray-600" />
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-bold text-gray-800">
                                            {enc.patient_detail?.name || "Unknown Patient"}
                                        </h4>
                                        <div className="mt-1 text-xs font-semibold text-gray-500">
                                            {new Date(enc.updated_at).toLocaleDateString()} ·{" "}
                                            {new Date(enc.updated_at).toLocaleTimeString([], {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                            })}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-1">
                                    <PriorityBadge priority={enc.priority} />
                                    <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600">
                                        <CheckCircle size={14} /> Completed
                                    </div>
                                </div>
                            </div>

                            {/* Location */}
                            {(enc.floor || enc.room_number) && (
                                <div className="mb-3 flex w-fit items-center gap-2 rounded-lg bg-gray-100 px-3 py-1.5 text-xs text-gray-600">
                                    <MapPin size={12} />
                                    {[
                                        enc.floor && `Floor ${enc.floor}`,
                                        enc.room_number && `Room ${enc.room_number}`,
                                        enc.bed_number && `Bed ${enc.bed_number}`,
                                    ]
                                        .filter(Boolean)
                                        .join(" · ")}
                                </div>
                            )}

                            {/* EMR Summary */}
                            {enc.assessment_detail && (
                                <div className="rounded-lg border-l-4 border-emerald-400 bg-white p-4 shadow-sm">
                                    <div className="mb-3 text-[10px] font-black uppercase tracking-wider text-emerald-600">
                                        EMR System Summary
                                    </div>
                                    <FormattedReport text={enc.assessment_detail.report_text} />

                                    {enc.assessment_detail.notes && (
                                        <div className="mt-4 border-t border-gray-200 pt-4">
                                            <div className="mb-1 text-[10px] font-black uppercase tracking-wider text-gray-500">
                                                Physician Progress Notes
                                            </div>
                                            <div className="rounded-lg bg-gray-50 p-3 text-sm italic text-gray-600">
                                                "{enc.assessment_detail.notes}"
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Assignments Page ────────────────────────────────────────────────────
function AssignmentsPage() {
    const { user } = useAuthStore();
    const [pending, setPending] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState({});
    const [rejectEnc, setRejectEnc] = useState(null);

    const load = useCallback(async () => {
        try {
            const all = await EncounterAPI.list({ status: "assigned" });
            const mine = Array.isArray(all)
                ? all.filter((e) => e.assigned_doctor === user?.id)
                : [];
            setPending(mine);
        } catch {
            setPending([]);
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        load();
        const t = setInterval(load, 15000);
        return () => clearInterval(t);
    }, [load]);

    const accept = async (enc) => {
        setActionLoading((prev) => ({ ...prev, [enc.id]: "accepting" }));
        try {
            await AllocationAPI.respond({ encounter_id: enc.id, accepted: true });
            load();
        } catch (err) {
            alert(err.response?.data?.errors || err.message);
        } finally {
            setActionLoading((prev) => ({ ...prev, [enc.id]: null }));
        }
    };

    if (loading)
        return (
            <div className="flex h-64 flex-col items-center justify-center gap-4 text-gray-500">
                <div className="relative">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
                </div>
                <span className="text-sm font-medium uppercase tracking-widest">
                    Loading assignments...
                </span>
            </div>
        );

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black tracking-tight text-gray-900">
                        <ClipboardList className="h-8 w-8 text-blue-600" /> Pending
                        Assignments
                    </h1>
                    <p className="mt-1 text-sm text-gray-500">
                        Accept or reject new cases — auto-refreshes every 15s
                    </p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white/70 px-4 py-2 text-sm font-semibold text-gray-700 backdrop-blur-sm transition-all hover:bg-white/80"
                >
                    <RefreshCw size={16} className="text-blue-500" /> Force Refresh
                </button>
            </div>

            {pending.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-gray-50/50 py-20 backdrop-blur-sm">
                    <div className="mb-4 text-5xl opacity-20">📭</div>
                    <p className="text-gray-500">No pending assignments for you</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {pending.map((enc) => (
                        <div
                            key={enc.id}
                            className="group rounded-2xl border border-gray-200 bg-white/70 p-5 shadow-lg backdrop-blur-sm transition-all hover:border-blue-200"
                        >
                            <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
                                <div className="flex w-full items-center gap-5 md:w-auto">
                                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-xl">
                                        <User className="h-6 w-6 text-blue-600" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <h4 className="text-lg font-bold text-gray-800">
                                                {enc.patient_detail?.name || "Patient"}
                                            </h4>
                                            <PriorityBadge priority={enc.priority} />
                                        </div>
                                        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-medium text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <Activity size={12} className="text-blue-500/50" />{" "}
                                                Score {enc.risk_score}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock size={12} className="text-amber-500/50" /> Wait{" "}
                                                {waitLabel(enc.created_at)}
                                            </span>
                                            <span className="flex items-center gap-1 text-blue-700">
                                                <MapPin size={12} /> F {enc.floor || "?"} · R{" "}
                                                {enc.room_number || "?"} · B {enc.bed_number || "?"}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex w-full items-center gap-3 md:w-auto">
                                    <button
                                        disabled={actionLoading[enc.id] === "accepting"}
                                        onClick={() => accept(enc)}
                                        className="flex-1 rounded-xl bg-emerald-600 px-8 py-2.5 text-sm font-bold text-white shadow-lg shadow-emerald-600/20 transition-all active:scale-95 disabled:opacity-50 md:flex-none"
                                    >
                                        {actionLoading[enc.id] === "accepting" ? (
                                            <span className="flex items-center justify-center gap-1">
                                                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                                ...
                                            </span>
                                        ) : (
                                            <>
                                                <CheckCircle size={16} className="inline mr-1" /> Accept
                                            </>
                                        )}
                                    </button>
                                    <button
                                        onClick={() => setRejectEnc(enc)}
                                        className="flex-1 rounded-xl border border-gray-300 bg-white/80 px-6 py-2.5 text-sm font-semibold text-gray-700 transition-all hover:bg-gray-100 md:flex-none"
                                    >
                                        <XCircle size={16} className="inline mr-1" /> Reject
                                    </button>
                                </div>
                            </div>

                            {enc.triage_data?.vitals_json && (
                                <div className="mt-4 flex flex-wrap gap-3 border-t border-gray-200 pt-4">
                                    {Object.entries(enc.triage_data.vitals_json)
                                        .filter(([, v]) => v != null)
                                        .slice(0, 4)
                                        .map(([k, v]) => (
                                            <div
                                                key={k}
                                                className="rounded-lg border border-gray-200 bg-gray-100/50 px-2 py-1 text-[10px] font-bold uppercase tracking-tighter text-gray-600"
                                            >
                                                {k}: <span className="ml-1 text-gray-800">{v}</span>
                                            </div>
                                        ))}
                                    <div className="ml-auto text-blue-400 opacity-50 transition-transform group-hover:translate-x-1">
                                        <ChevronRight size={16} />
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
            {rejectEnc && (
                <RejectModal
                    encounter={rejectEnc}
                    onClose={() => setRejectEnc(null)}
                    onDone={load}
                />
            )}
        </div>
    );
}

export default function DoctorDashboard() {
    return (
        <Shell>
            <Routes>
                <Route index element={<Navigate to="my-cases" replace />} />
                <Route path="my-cases" element={<MyCasesPage />} />
                <Route path="assignments" element={<AssignmentsPage />} />
                <Route path="history" element={<PatientHistoryPage />} />
            </Routes>
        </Shell>
    );
}

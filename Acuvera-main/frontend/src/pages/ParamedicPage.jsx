import React, { useState } from "react";
import { AmbulanceAPI } from "../api/client";
import {
  Ambulance,
  Clock,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Heart,
  Activity,
  Thermometer,
  Droplets,
  Brain,
  AlertCircle,
  X,
} from "lucide-react";

const VITALS_FIELDS = [
  {
    key: "hr",
    label: "Heart Rate",
    unit: "bpm",
    placeholder: "72",
    icon: Heart,
  },
  { key: "spo2", label: "SpO₂", unit: "%", placeholder: "98", icon: Droplets },
  {
    key: "bp_systolic",
    label: "BP Systolic",
    unit: "mmHg",
    placeholder: "120",
    icon: Activity,
  },
  {
    key: "bp_diastolic",
    label: "BP Diastolic",
    unit: "mmHg",
    placeholder: "80",
    icon: Activity,
  },
  {
    key: "rr",
    label: "Resp. Rate",
    unit: "/min",
    placeholder: "16",
    icon: Activity,
  },
  {
    key: "temp",
    label: "Temperature",
    unit: "°F",
    placeholder: "98.6",
    icon: Thermometer,
  },
  { key: "gcs", label: "GCS", unit: "/15", placeholder: "15", icon: Brain },
  {
    key: "pain_score",
    label: "Pain Score",
    unit: "/10",
    placeholder: "5",
    icon: AlertCircle,
  },
];

const SYMPTOM_OPTIONS = [
  "chest_pain",
  "shortness_of_breath",
  "trauma",
  "stroke_symptoms",
  "seizure",
  "syncope",
  "altered_mental_status",
  "severe_abdominal_pain",
  "sweating",
  "severe_headache",
];

const RED_FLAGS = [
  "cardiac_arrest",
  "no_pulse",
  "severe_hemorrhage",
  "airway_compromised",
];

export default function ParamedicPage() {
  const [form, setForm] = useState({
    patient_name: "",
    age: "",
    gender: "unknown",
    chief_complaint: "",
    eta_minutes: "5",
    vitals: {},
    symptoms: [],
    red_flags: {},
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const setVital = (key, val) => {
    const num = parseFloat(val);
    setForm((f) => ({
      ...f,
      vitals: { ...f.vitals, [key]: isNaN(num) ? undefined : num },
    }));
  };

  const toggleSymptom = (s) => {
    setForm((f) => ({
      ...f,
      symptoms: f.symptoms.includes(s)
        ? f.symptoms.filter((x) => x !== s)
        : [...f.symptoms, s],
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...form,
        age: parseInt(form.age) || undefined,
        eta_minutes: parseInt(form.eta_minutes) || 5,
        vitals: Object.fromEntries(
          Object.entries(form.vitals).filter(([, v]) => v !== undefined),
        ),
      };
      const data = await AmbulanceAPI.preRegister(payload);
      setResult(data);
    } catch (e) {
      setError(
        e.response?.data?.message ||
          "Submission failed. Check your connection.",
      );
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-rose-50 to-indigo-50 p-8">
        <div className="max-w-md w-full bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-8 shadow-2xl text-center">
          <div className="flex justify-center mb-4">
            <div className="w-20 h-20 rounded-full bg-rose-100 flex items-center justify-center">
              <Ambulance size={40} className="text-rose-600" />
            </div>
          </div>
          <CheckCircle size={48} className="mx-auto mb-4 text-emerald-600" />
          <h2 className="text-2xl font-black text-gray-800 mb-2">
            Patient Pre-Registered
          </h2>
          <p className="text-gray-600 mb-6">{result.message}</p>
          <div className="bg-rose-50/80 border border-rose-200 rounded-2xl p-6 mb-6 backdrop-blur-sm">
            <div className="text-sm font-bold uppercase tracking-wider text-rose-700 mb-2">
              🚨 PATIENT ALERT — INCOMING IN
            </div>
            <div className="text-5xl font-black text-rose-600">
              {result.eta_minutes} min
            </div>
            <div className="text-sm text-gray-500 mt-2">
              Dept: {result.department}
            </div>
          </div>
          <button
            onClick={() => {
              setResult(null);
              setForm({
                patient_name: "",
                age: "",
                gender: "unknown",
                chief_complaint: "",
                eta_minutes: "5",
                vitals: {},
                symptoms: [],
                red_flags: {},
              });
            }}
            className="w-full bg-gradient-to-r from-rose-600 to-rose-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-rose-500/30 active:scale-[0.98] transition-all"
          >
            Register Another Patient
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-white to-indigo-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white/70 backdrop-blur-xl border-b border-white/50 px-4 sm:px-6 py-4 flex items-center gap-4 shadow-sm">
        <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center">
          <Ambulance size={20} className="text-rose-600" />
        </div>
        <div>
          <h1 className="text-lg font-black text-gray-800 flex items-center gap-2">
            🚑 Ambulance Pre-Triage
          </h1>
          <p className="text-xs text-gray-500">
            Acuvera Paramedic Portal — register patient en route
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-50 border border-rose-200">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          </span>
          <span className="text-[10px] font-black uppercase tracking-wider text-rose-700">
            LIVE
          </span>
        </div>
      </div>

      {/* Main Form */}
      <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
        <form onSubmit={submit} className="space-y-6">
          {/* Patient Information */}
          <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-6 shadow-lg">
            <h3 className="text-xs font-black uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-rose-500 rounded-full" />
              Patient Information
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Name (if known)
                </label>
                <input
                  value={form.patient_name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, patient_name: e.target.value }))
                  }
                  placeholder="Unknown"
                  className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500 outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Age
                </label>
                <input
                  type="number"
                  value={form.age}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, age: e.target.value }))
                  }
                  placeholder="65"
                  min={1}
                  max={120}
                  className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500 outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Gender
                </label>
                <select
                  value={form.gender}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, gender: e.target.value }))
                  }
                  className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500 outline-none transition-all appearance-none"
                >
                  <option value="unknown">Unknown</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  ETA (minutes) *
                </label>
                <input
                  type="number"
                  value={form.eta_minutes}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, eta_minutes: e.target.value }))
                  }
                  required
                  min={1}
                  max={120}
                  className="w-full bg-white/80 border border-rose-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500 outline-none transition-all"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                Chief Complaint / Notes
              </label>
              <input
                value={form.chief_complaint}
                onChange={(e) =>
                  setForm((f) => ({ ...f, chief_complaint: e.target.value }))
                }
                placeholder="e.g. 65M chest pain 30min, diaphoresis, BP 90/60"
                className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500 outline-none transition-all"
              />
            </div>
          </div>

          {/* Two-column layout for Vitals & Symptoms */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Vitals */}
            <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-6 shadow-lg">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
                <span className="w-1.5 h-4 bg-indigo-500 rounded-full" />
                Vitals
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {VITALS_FIELDS.map((f) => {
                  const Icon = f.icon;
                  return (
                    <div key={f.key}>
                      <label className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                        <Icon size={12} className="text-gray-400" />
                        {f.label}{" "}
                        <span className="text-gray-400">({f.unit})</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder={f.placeholder}
                        onChange={(e) => setVital(f.key, e.target.value)}
                        className="w-full bg-white/80 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all"
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Symptoms & Red Flags */}
            <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-6 shadow-lg">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
                <span className="w-1.5 h-4 bg-amber-500 rounded-full" />
                Symptoms & Red Flags
              </h3>
              <div className="flex flex-wrap gap-2 mb-6">
                {SYMPTOM_OPTIONS.map((s) => {
                  const active = form.symptoms.includes(s);
                  return (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSymptom(s)}
                      className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${
                        active
                          ? "bg-amber-100 text-amber-700 border border-amber-200"
                          : "bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200"
                      }`}
                    >
                      {s.replace(/_/g, " ")}
                    </button>
                  );
                })}
              </div>

              <div>
                <div className="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-3">
                  Red Flags
                </div>
                <div className="space-y-2">
                  {RED_FLAGS.map((flag) => (
                    <label
                      key={flag}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={!!form.red_flags[flag]}
                        onChange={(e) =>
                          setForm((f) => ({
                            ...f,
                            red_flags: {
                              ...f.red_flags,
                              [flag]: e.target.checked,
                            },
                          }))
                        }
                        className="w-4 h-4 rounded border-gray-300 text-rose-600 focus:ring-rose-500"
                      />
                      <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">
                        ⚠️ {flag.replace(/_/g, " ")}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-rose-50/80 border border-rose-200 rounded-xl p-4 text-rose-700 text-sm flex items-center gap-2 backdrop-blur-sm">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white font-bold py-4 rounded-xl shadow-lg shadow-rose-500/30 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Registering Patient...
              </>
            ) : (
              <>
                <Ambulance size={18} />
                Alert Hospital — Patient En Route
                <ChevronRight size={18} />
              </>
            )}
          </button>

          <div className="text-center text-[10px] text-gray-400 mt-4">
            🔒 Secured with ambulance authorization key · Acuvera Emergency
            Network
          </div>
        </form>
      </div>
    </div>
  );
}

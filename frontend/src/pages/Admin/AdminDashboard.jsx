import { useState, useEffect, useCallback, useRef } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
  Cell,
} from "recharts";
import {
  MessageSquare,
  X,
  Send,
  Bot,
  Activity,
  AlertTriangle,
  Clock,
  Users,
  Stethoscope,
  Gauge,
  TrendingUp,
  Bell,
  RefreshCw,
  Trash2,
  User,
  HeartPulse,
  Timer,
  Hospital,
  BarChart3,
  AlertCircle,
  CheckCircle2,
  Zap,
  ChevronDown, // ← add this
  Settings,
  Pencil,
  Shield,
  UserPlus,
  Edit,
  Mail,
  Building2,
  Key,
  // Simulation
  Rocket,
  FlaskConical,
  Target,
} from "lucide-react";
import Shell from "../../components/Shell";
import { AdminAPI, AuthAPI, SimulateAPI } from "../../api/client";

// ─── Overview Page ────────────────────────────────────────────
function OverviewPage() {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [clearMsg, setClearMsg] = useState(null);

  const load = useCallback(async () => {
    try {
      const [overview, starvation] = await Promise.all([
        AdminAPI.overview(),
        AdminAPI.starvationAlerts(),
      ]);
      setData(overview);
      setAlerts(Array.isArray(starvation) ? starvation : []);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  const handleClearAll = async (e) => {
    const withPatients = e?.shiftKey;
    const msg = withPatients
      ? "Delete ALL encounters AND simulation patients? This cannot be undone."
      : "Soft-delete ALL encounters (patients are kept)? This is reversible.";
    if (!window.confirm(msg)) return;
    setClearing(true);
    setClearMsg(null);
    try {
      const result = await AdminAPI.clearEncounters(
        withPatients ? "all" : "encounters",
      );
      setClearMsg({
        type: "success",
        text: `Cleared ${result.encounters_cleared} encounter(s)${result.patients_cleared > 0 ? ` and ${result.patients_cleared} patient(s)` : ""}.`,
      });
      await load();
    } catch (err) {
      setClearMsg({
        type: "danger",
        text: err.response?.data?.errors || err.message,
      });
    } finally {
      setClearing(false);
      setTimeout(() => setClearMsg(null), 5000);
    }
  };

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-gray-200 rounded-full" />
          <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
        </div>
        <span className="text-sm font-medium tracking-widest text-gray-500 uppercase">
          Analyzing Operations...
        </span>
      </div>
    );

  const priority_dist = data?.priority_distribution || {
    critical: 0,
    high: 0,
    moderate: 0,
    low: 0,
  };
  const priorityChartData = Object.entries(priority_dist).map(
    ([name, value]) => ({ name, value }),
  );

  // CSS variables for colors
  const COLOR_MAP = {
    critical: "var(--critical)",
    high: "var(--high)",
    moderate: "var(--moderate)",
    low: "var(--low)",
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100/50 backdrop-blur-sm border border-blue-200/50 shadow-sm">
              <Activity className="w-6 h-6 text-blue-600" />
            </span>
            Operations Overview
          </h1>
          <p className="text-sm mt-2 text-gray-500 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Live system status — auto-refreshes every 60s
          </p>
        </div>

        <div className="flex items-center gap-3">
          {clearMsg && (
            <div className={`px-4 py-2 rounded-xl text-xs font-semibold backdrop-blur-sm border ${clearMsg.type === "success"
              ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
              : "bg-rose-50/80 border-rose-200 text-rose-700"
              }`}>
              {clearMsg.type === "success" ? (
                <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 inline mr-1.5" />
              )}
              {clearMsg.text}
            </div>
          )}

          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:scale-105 active:scale-95 bg-rose-50/80 backdrop-blur-sm border border-rose-200 text-rose-600 hover:bg-rose-100/80 shadow-sm"
            onClick={handleClearAll}
            disabled={clearing}
            title="Shift+Click to also delete simulation patients"
          >
            {clearing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Clearing...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Clear Encounters
              </>
            )}
          </button>

          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:scale-105 active:scale-95 bg-white/80 backdrop-blur-sm border border-gray-200 text-gray-700 hover:bg-white/90 shadow-sm"
            onClick={load}
          >
            <RefreshCw className="w-4 h-4 text-blue-500" />
            Refresh Metrics
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          {
            label: "Active Patients",
            value: data?.active_patients ?? 0,
            icon: Users,
            gradient: "from-blue-500 to-indigo-500",
            bgLight: "bg-blue-50/80",
            borderLight: "border-blue-200",
            textColor: "text-blue-600",
            trend: data?.active_patients > 10 ? `${data.active_patients}` : "Normal",
            trendUp: data?.active_patients <= 10,
          },
          {
            label: "Critical / High",
            value: `${priority_dist.critical} / ${priority_dist.high}`,
            icon: AlertTriangle,
            gradient: "from-rose-500 to-pink-500",
            bgLight: "bg-rose-50/80",
            borderLight: "border-rose-200",
            textColor: "text-rose-600",
            trend: priority_dist.critical > 0 ? `${priority_dist.critical} Critical` : "Clear",
            trendUp: priority_dist.critical === 0,
          },
          {
            label: "Avg Wait",
            value: data?.avg_wait_time_seconds ? `${Math.floor(data.avg_wait_time_seconds / 60)}m` : "—",
            icon: Timer,
            gradient: "from-amber-500 to-orange-500",
            bgLight: "bg-amber-50/80",
            borderLight: "border-amber-200",
            textColor: "text-amber-600",
            trend: data?.avg_wait_time_seconds > 1800 ? "Overdue" : "OK",
            trendUp: (data?.avg_wait_time_seconds || 0) < 900,
          },
          {
            label: "Starving",
            value: data?.starvation_count ?? 0,
            icon: AlertCircle,
            gradient: data?.starvation_count > 0 ? "from-rose-500 to-pink-500" : "from-emerald-500 to-green-500",
            bgLight: data?.starvation_count > 0 ? "bg-rose-50/80" : "bg-emerald-50/80",
            borderLight: data?.starvation_count > 0 ? "border-rose-200" : "border-emerald-200",
            textColor: data?.starvation_count > 0 ? "text-rose-600" : "text-emerald-600",
            trend: data?.starvation_count > 0 ? `${data.starvation_count} cases` : "All OK",
            trendUp: data?.starvation_count === 0,
          },
          {
            label: "Overloaded Drs",
            value: data?.overloaded_doctors ?? 0,
            icon: Stethoscope,
            gradient: data?.overloaded_doctors > 0 ? "from-rose-500 to-pink-500" : "from-emerald-500 to-green-500",
            bgLight: data?.overloaded_doctors > 0 ? "bg-rose-50/80" : "bg-emerald-50/80",
            borderLight: data?.overloaded_doctors > 0 ? "border-rose-200" : "border-emerald-200",
            textColor: data?.overloaded_doctors > 0 ? "text-rose-600" : "text-emerald-600",
            trend: data?.overloaded_doctors > 0 ? "Overloaded" : "Balanced",
            trendUp: data?.overloaded_doctors === 0,
          },
          {
            label: "Doctor Util %",
            value: data?.total_doctors > 0 ? `${Math.round(((data.total_doctors - (data.overloaded_doctors ?? 0)) / data.total_doctors) * 85 + (data.overloaded_doctors ?? 0) * 15)}%` : "—",
            icon: Gauge,
            gradient: "from-violet-500 to-purple-500",
            bgLight: "bg-violet-50/80",
            borderLight: "border-violet-200",
            textColor: "text-violet-600",
            trend: data?.total_doctors > 0 ? `${data.total_doctors} Total` : "—",
            trendUp: (data?.overloaded_doctors ?? 0) === 0,
          },
          {
            label: "Queue Load",
            value: (data?.starvation_count ?? 0) > 3 || priority_dist.critical + priority_dist.high > 5 ? "High" : (data?.starvation_count ?? 0) > 0 ? "Medium" : "Normal",
            icon: BarChart3,
            gradient: (data?.starvation_count ?? 0) > 3 ? "from-rose-500 to-pink-500" : "from-amber-500 to-orange-500",
            bgLight: (data?.starvation_count ?? 0) > 3 ? "bg-rose-50/80" : "bg-amber-50/80",
            borderLight: (data?.starvation_count ?? 0) > 3 ? "border-rose-200" : "border-amber-200",
            textColor: (data?.starvation_count ?? 0) > 3 ? "text-rose-600" : "text-amber-600",
            trend: `${data?.active_patients ?? 0} Active`,
            trendUp: (data?.starvation_count ?? 0) === 0,
          },
          {
            label: "Predicted Wait",
            value: data?.avg_wait_time_seconds ? `${Math.floor((data.avg_wait_time_seconds + (data.starvation_count ?? 0) * 300) / 60)}m` : "—",
            icon: TrendingUp,
            gradient: "from-fuchsia-500 to-pink-500",
            bgLight: "bg-fuchsia-50/80",
            borderLight: "border-fuchsia-200",
            textColor: "text-fuchsia-600",
            trend: (data?.avg_wait_time_seconds || 0) > 1800 ? "Long" : "Short",
            trendUp: (data?.avg_wait_time_seconds || 0) < 900,
          },
        ].map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="group relative rounded-2xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg"
              style={{
                background: "rgba(255, 255, 255, 0.7)",
                backdropFilter: "blur(12px)",
              }}
            >
              {/* Gradient overlay on hover */}
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${s.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

              <div className="relative">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${s.bgLight} border ${s.borderLight} backdrop-blur-sm group-hover:scale-110 transition-transform duration-300`}>
                      <Icon className={`w-5 h-5 ${s.textColor}`} />
                    </div>
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">
                      {s.label}
                    </span>
                  </div>
                  <span className={`text-[10px] font-black tracking-widest px-2 py-1 rounded-md border backdrop-blur-sm ${s.trendUp
                    ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
                    : "bg-rose-50/80 border-rose-200 text-rose-700"
                    }`}>
                    {s.trendUp ? "↓" : "↑"} {s.trend}
                  </span>
                </div>
                <div className={`text-4xl font-black tracking-tighter ${s.textColor}`}>
                  {s.value}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Priority Distribution */}
        <div className="rounded-2xl p-6 bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-xs font-black uppercase tracking-widest pl-3 text-gray-500 border-l-2 border-blue-500">
              Priority Distribution
            </h3>
          </div>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={priorityChartData} barCategoryGap="25%">
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#e5e7eb"
                  opacity={0.5}
                />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#6b7280", fontSize: 10, fontWeight: 700 }}
                  className="uppercase tracking-tighter"
                />
                <YAxis hide />
                <Tooltip
                  cursor={{ fill: "rgba(0,0,0,0.02)" }}
                  contentStyle={{
                    backgroundColor: "rgba(255,255,255,0.9)",
                    backdropFilter: "blur(8px)",
                    borderRadius: "12px",
                    border: "1px solid rgba(229,231,235,0.5)",
                    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1)",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "#111827" }}
                />
                <Bar
                  dataKey="value"
                  radius={[8, 8, 0, 0]}
                  isAnimationActive={true}
                  animationDuration={1000}
                  animationEasing="ease-out"
                >
                  {priorityChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLOR_MAP[entry.name] || "#3b82f6"}
                      opacity={0.9}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Starvation alerts */}
        <div className="lg:col-span-2 rounded-2xl p-6 bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xs font-black uppercase tracking-widest pl-3 text-gray-500 border-l-2 border-rose-500">
              🚨 Critical Starvation Alerts
            </h3>
            {alerts.length > 0 && (
              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest animate-pulse bg-rose-50/80 backdrop-blur-sm border border-rose-200 text-rose-600">
                <Zap className="w-3 h-3 inline mr-1" />
                {alerts.length} Flagged
              </span>
            )}
          </div>

          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <div className="text-4xl mb-4 p-4 rounded-full bg-emerald-50/80 backdrop-blur-sm border border-emerald-200 text-emerald-600">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <p className="font-bold text-sm text-gray-900">
                All operations within SLA thresholds
              </p>
              <p className="text-xs uppercase tracking-widest mt-1 opacity-60">
                No starving encounters detected
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {alerts.map((enc) => (
                <div
                  key={enc.id}
                  className="rounded-xl p-4 flex items-center gap-4 transition-all cursor-default group bg-white/50 backdrop-blur-sm border border-gray-200/50 hover:bg-white/80 hover:shadow-md"
                >
                  <div
                    className={`w-1.5 h-12 rounded-full shrink-0 ${enc.priority === "critical"
                      ? "bg-rose-500"
                      : enc.priority === "high"
                        ? "bg-orange-500"
                        : "bg-amber-500"
                      }`}
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-sm font-bold leading-none tracking-tight text-gray-900">
                        {enc.patient_detail?.name || "Patient"}
                      </span>
                      <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded border bg-rose-50/80 border-rose-200 text-rose-600 backdrop-blur-sm">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {enc.wait_minutes}m
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">
                        {enc.priority}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-gray-300" />
                      <span className="text-[10px] font-medium uppercase tracking-wider truncate text-gray-400">
                        Overdue by {enc.wait_minutes - (enc.threshold_minutes || 60)}m
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


// ─── Forecast Page ────────────────────────────────────────────
function ForecastPage() {
  const [depts, setDepts] = useState([]);
  const [selectedDept, setSelectedDept] = useState("");
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    AdminAPI.departments()
      .then((d) => {
        setDepts(Array.isArray(d) ? d : []);
        if (d?.[0]) setSelectedDept(d[0].id);
      })
      .catch(() => { });
  }, []);

  useEffect(() => {
    if (!selectedDept) return;
    setLoading(true);
    AdminAPI.forecast({ department: selectedDept })
      .then(setForecast)
      .catch(() => setForecast(null))
      .finally(() => setLoading(false));
  }, [selectedDept]);

  const chartData = forecast
    ? Object.entries(forecast.hourly_forecast || {}).map(([hour, f]) => ({
      hour: `${hour}:00`,
      expected: f.expected,
      low: f.low,
      high: f.high,
    }))
    : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/50 backdrop-blur-sm border border-emerald-200/50 shadow-sm">
              <TrendingUp className="w-6 h-6 text-emerald-600" />
            </span>
            Peak Hour Forecast
          </h1>
          <p className="text-sm mt-2 text-gray-500 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Exponential smoothing model · 90-day historical baseline
          </p>
        </div>

        {/* Department Selector */}
        <div className="relative">
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="appearance-none pl-4 pr-10 py-2.5 rounded-xl text-sm font-semibold cursor-pointer transition-all focus:outline-none bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg text-gray-700 hover:bg-white/80"
            style={{ minWidth: 200 }}
          >
            {depts.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-72 gap-4 text-gray-500">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-gray-200 rounded-full" />
            <div className="absolute top-0 left-0 w-12 h-12 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin" />
          </div>
          <span className="text-sm font-medium tracking-widest uppercase">
            Computing forecast...
          </span>
        </div>
      ) : !forecast ? (
        <div className="flex flex-col items-center justify-center py-24 rounded-3xl border border-dashed bg-gray-50/50 backdrop-blur-sm border-gray-200">
          <BarChart3 className="w-16 h-16 text-gray-300 mb-4" />
          <p className="font-medium text-gray-700">No forecast data yet</p>
          <p className="text-sm mt-1 text-gray-400">
            Requires 90+ days of patient history
          </p>
        </div>
      ) : (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {[
              {
                label: "Peak Hour",
                value: `${forecast.peak_hour}:00`,
                sub: `${forecast.peak_expected_count} expected arrivals`,
                icon: Clock,
                gradient: "from-blue-500 to-indigo-500",
                bgLight: "bg-blue-50/80",
                borderLight: "border-blue-200",
                textColor: "text-blue-600",
              },
              {
                label: "Recommended Doctors",
                value: forecast.staffing_suggestion?.recommended_doctors,
                sub: `Target wait: ${forecast.staffing_suggestion?.target_avg_wait_minutes} min`,
                icon: Stethoscope,
                gradient: "from-emerald-500 to-green-500",
                bgLight: "bg-emerald-50/80",
                borderLight: "border-emerald-200",
                textColor: "text-emerald-600",
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.label}
                  className="group relative rounded-2xl p-6 flex items-center gap-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg"
                >
                  <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${s.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />
                  <div className={`p-3 rounded-2xl ${s.bgLight} border ${s.borderLight} backdrop-blur-sm group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className={`w-6 h-6 ${s.textColor}`} />
                  </div>
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-1">
                      {s.label}
                    </div>
                    <div className={`text-4xl font-black tracking-tighter ${s.textColor}`}>
                      {s.value}
                    </div>
                    <div className="text-xs mt-1 font-medium text-gray-500">
                      {s.sub}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Chart Card */}
          <div className="rounded-3xl p-6 bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-xs font-black uppercase tracking-widest pl-3 text-gray-500 border-l-2 border-emerald-500">
                  Hourly Arrival Forecast
                </h3>
                <p className="text-xs mt-1 font-medium text-gray-500">
                  Projected over the next 7 days
                </p>
              </div>
              <div className="flex items-center gap-5 text-xs font-semibold text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full inline-block bg-blue-500" /> Expected
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full inline-block bg-orange-500" /> High
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full inline-block bg-emerald-500" /> Low
                </span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart
                data={chartData}
                margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="gradExpected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.1} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#e5e7eb"
                  opacity={0.5}
                />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "#6b7280", fontSize: 10, fontWeight: 700 }}
                  axisLine={false}
                  tickLine={false}
                  interval={2}
                />
                <YAxis
                  tick={{ fill: "#6b7280", fontSize: 10, fontWeight: 700 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(255,255,255,0.9)",
                    backdropFilter: "blur(8px)",
                    borderRadius: "12px",
                    border: "1px solid rgba(229,231,235,0.5)",
                    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1)",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                  labelStyle={{ color: "#111827", marginBottom: 4 }}
                />
                <Legend wrapperStyle={{ display: "none" }} />
                <Area
                  type="monotone"
                  dataKey="expected"
                  stroke="#3b82f6"
                  fill="url(#gradExpected)"
                  strokeWidth={2.5}
                  name="Expected"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="high"
                  stroke="#f97316"
                  fill="url(#gradHigh)"
                  strokeDasharray="5 3"
                  strokeWidth={1.5}
                  name="High estimate"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="low"
                  stroke="#10b981"
                  fill="none"
                  strokeDasharray="5 3"
                  strokeWidth={1.5}
                  name="Low estimate"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}



// ─── Config Page ──────────────────────────────────────────────
function ConfigPage() {
  const [config, setConfig] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  // Dept Form State
  const [deptForm, setDeptForm] = useState({
    name: "",
    starvation_threshold_minutes: 60,
    profile_type: "general",
  });
  const [editingDeptId, setEditingDeptId] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [c, d] = await Promise.all([
        AdminAPI.config(),
        AdminAPI.departments(),
      ]);
      setConfig(c || {});
      setDepartments(Array.isArray(d) ? d : []);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const saveConfig = async () => {
    setSaving(true);
    try {
      await AdminAPI.updateConfig(config);
      setMsg({
        type: "success",
        text: "Hospital configuration saved successfully.",
      });
    } catch (err) {
      setMsg({
        type: "danger",
        text: "Failed to save: " + (err.response?.data?.errors || err.message),
      });
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(null), 3000);
    }
  };

  const handleDeptSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDeptId) {
        await AdminAPI.updateDepartment(editingDeptId, deptForm);
        setMsg({ type: "success", text: "Department updated." });
      } else {
        await AdminAPI.createDepartment(deptForm);
        setMsg({ type: "success", text: "New department added." });
      }
      setDeptForm({
        name: "",
        starvation_threshold_minutes: 60,
        profile_type: "general",
      });
      setEditingDeptId(null);
      loadData();
    } catch (err) {
      setMsg({
        type: "danger",
        text:
          "Operation failed: " + (err.response?.data?.errors || err.message),
      });
    } finally {
      setTimeout(() => setMsg(null), 3000);
    }
  };

  const toggleDeptStatus = async (id) => {
    try {
      await AdminAPI.deleteDepartment(id);
      loadData();
    } catch (err) {
      setMsg({ type: "danger", text: "Failed to update department status." });
    }
  };

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4 text-gray-500">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-gray-200 rounded-full" />
          <div className="absolute top-0 left-0 w-12 h-12 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
        </div>
        <span className="text-sm font-medium tracking-widest uppercase italic opacity-80">
          Loading secure config...
        </span>
      </div>
    );

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100/50 backdrop-blur-sm border border-blue-200/50 shadow-sm">
              <Settings className="w-6 h-6 text-blue-600" />
            </span>
            Hospital Control
          </h1>
          <p className="text-sm mt-2 text-gray-500">
            Configure clinical thresholds and manage departments
          </p>
        </div>
        {msg && (
          <div
            className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest border animate-in zoom-in-95 duration-300 backdrop-blur-sm ${msg.type === "success"
              ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
              : "bg-rose-50/80 border-rose-200 text-rose-700"
              }`}
          >
            {msg.type === "success" ? (
              <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 inline mr-1.5" />
            )}
            {msg.text}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Hospital Config */}
        <div className="space-y-6">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-xs font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-4 bg-blue-500 rounded-full" />
              Global Configuration
            </h2>
            <button
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-blue-500/20 backdrop-blur-sm"
              onClick={saveConfig}
              disabled={saving}
            >
              {saving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 inline mr-1.5 animate-spin" />
                  Processing...
                </>
              ) : (
                "Save All Changes"
              )}
            </button>
          </div>

          {config ? (
            <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-6 space-y-6 shadow-xl">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Hospital Name
                </label>
                <input
                  className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all placeholder:text-gray-400"
                  value={config.hospital_name || ""}
                  onChange={(e) =>
                    setConfig((c) => ({ ...c, hospital_name: e.target.value }))
                  }
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                    Cases / Doctor
                  </label>
                  <input
                    type="number"
                    className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                    value={config.max_active_cases_per_doctor || 6}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        max_active_cases_per_doctor: parseInt(e.target.value),
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                    Avg Revenue (₹)
                  </label>
                  <input
                    type="number"
                    className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                    value={config.avg_revenue_per_patient || 500}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        avg_revenue_per_patient: parseFloat(e.target.value),
                      }))
                    }
                  />
                </div>
              </div>

              <div className="pt-4 space-y-4">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-gray-200 pb-2">
                  SLA Thresholds (Seconds)
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {[
                    ["sla_code_blue_seconds", "Code Blue"],
                    ["sla_trauma_seconds", "Trauma"],
                    ["sla_manual_seconds", "Manual"],
                  ].map(([k, lbl]) => (
                    <div className="space-y-2" key={k}>
                      <label className="text-[10px] font-bold text-gray-500 uppercase tracking-tighter pl-1">
                        {lbl}
                      </label>
                      <input
                        type="number"
                        className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2 text-sm text-gray-700 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                        value={config[k] || ""}
                        onChange={(e) =>
                          setConfig((c) => ({
                            ...c,
                            [k]: parseInt(e.target.value),
                          }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-4 space-y-3">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-gray-200 pb-2">
                  Operational Feature Flags
                </h3>
                <div className="grid grid-cols-1 gap-2">
                  {Object.keys(config.feature_flags || {})
                    .sort()
                    .map((flag) => (
                      <div
                        key={flag}
                        className="flex items-center justify-between p-3 rounded-xl bg-gray-50/50 border border-gray-200/50 hover:border-gray-300 transition-colors group backdrop-blur-sm"
                      >
                        <span className="text-xs font-bold text-gray-600 group-hover:text-gray-800 transition-colors capitalize">
                          {flag.replace(/_/g, " ")}
                        </span>
                        <button
                          className={`px-3 py-1 text-[10px] font-black rounded-lg active:scale-90 border transition-all duration-300 backdrop-blur-sm ${config.feature_flags[flag]
                            ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
                            : "bg-white/50 border-gray-200 text-gray-500"
                            }`}
                          onClick={() =>
                            setConfig((c) => ({
                              ...c,
                              feature_flags: {
                                ...c.feature_flags,
                                [flag]: !c.feature_flags[flag],
                              },
                            }))
                          }
                        >
                          {config.feature_flags[flag] ? "ENABLED" : "DISABLED"}
                        </button>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-12 text-center text-gray-500 italic">
              System configuration sync failed...
            </div>
          )}
        </div>

        {/* Departments Section */}
        <div className="space-y-6">
          <h2 className="text-xs font-black text-gray-500 uppercase tracking-widest px-2 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-emerald-500 rounded-full" />
            Clinical Departments
          </h2>

          {/* Add/Edit Form */}
          <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-gray-700 mb-6 flex items-center gap-2">
              {editingDeptId ? (
                <>
                  <span className="text-blue-600 font-black">EDIT</span>
                  Modifying {deptForm.name}
                </>
              ) : (
                <>
                  <span className="text-emerald-600 font-black">NEW</span>
                  Register Department
                </>
              )}
            </h3>
            <form onSubmit={handleDeptSubmit} className="space-y-5">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Department Name
                </label>
                <input
                  className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all placeholder:text-gray-400"
                  value={deptForm.name}
                  onChange={(e) =>
                    setDeptForm({ ...deptForm, name: e.target.value })
                  }
                  required
                  placeholder="e.g. Intensive Care Unit"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                    Starve Threshold (m)
                  </label>
                  <input
                    type="number"
                    className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all"
                    value={deptForm.starvation_threshold_minutes}
                    onChange={(e) =>
                      setDeptForm({
                        ...deptForm,
                        starvation_threshold_minutes: parseInt(e.target.value),
                      })
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                    Clinical Profile
                  </label>
                  <select
                    className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all appearance-none"
                    value={deptForm.profile_type}
                    onChange={(e) =>
                      setDeptForm({ ...deptForm, profile_type: e.target.value })
                    }
                  >
                    <option value="general">General Ward</option>
                    <option value="emergency">Emergency Response</option>
                    <option value="critical_care">Critical Care</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
                >
                  {editingDeptId ? "Update Identity" : "Commission Department"}
                </button>
                {editingDeptId && (
                  <button
                    type="button"
                    className="px-6 bg-gray-100/50 hover:bg-gray-200/50 text-gray-600 font-bold rounded-xl transition-all active:scale-95 backdrop-blur-sm"
                    onClick={() => {
                      setEditingDeptId(null);
                      setDeptForm({
                        name: "",
                        starvation_threshold_minutes: 60,
                        profile_type: "general",
                      });
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Department List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2">
              <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">
                Active Units
              </h3>
              <span className="text-[10px] font-bold text-gray-500">
                {departments.length} Units
              </span>
            </div>
            {departments.length === 0 ? (
              <p className="text-center py-6 text-xs text-gray-500 italic uppercase tracking-widest opacity-50 bg-white/50 backdrop-blur-sm border border-white/50 rounded-2xl">
                No clinical units operational
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {departments.map((d) => (
                  <div
                    key={d.id}
                    className="group flex items-center justify-between p-4 rounded-xl bg-white/50 backdrop-blur-sm border border-white/50 hover:bg-white/80 hover:border-gray-200 transition-all shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-1 h-8 rounded-full ${d.profile_type === "critical_care"
                          ? "bg-rose-500"
                          : d.profile_type === "emergency"
                            ? "bg-amber-500"
                            : "bg-blue-500"
                          }`}
                      />
                      <div>
                        <div className="text-sm font-bold text-gray-700 group-hover:text-gray-800 transition-colors">
                          {d.name}
                        </div>
                        <div className="text-[10px] font-medium text-gray-500 flex items-center gap-2 uppercase tracking-tight">
                          SLA: {d.starvation_threshold_minutes}m
                          <span className="w-1 h-1 bg-gray-300 rounded-full" />
                          {d.profile_type.replace(/_/g, " ")}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50/50 rounded-lg transition-all"
                        title="Edit Department"
                        onClick={() => {
                          setEditingDeptId(d.id);
                          setDeptForm({
                            name: d.name,
                            starvation_threshold_minutes:
                              d.starvation_threshold_minutes,
                            profile_type: d.profile_type,
                          });
                        }}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 text-gray-500 hover:text-rose-600 hover:bg-rose-50/50 rounded-lg transition-all"
                        title="Decommission"
                        onClick={() => toggleDeptStatus(d.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


// ─── Starvation Page ──────────────────────────────────────────
function StarvationPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [depts, setDepts] = useState([]);
  const [dept, setDept] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await AdminAPI.starvationAlerts(
        dept ? { department: dept } : {},
      );
      setAlerts(Array.isArray(data) ? data : []);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [dept]);

  useEffect(() => {
    AdminAPI.departments()
      .then((d) => setDepts(Array.isArray(d) ? d : []))
      .catch(() => { });
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case "critical": return <AlertTriangle className="w-3.5 h-3.5" />;
      case "high": return <Zap className="w-3.5 h-3.5" />;
      case "moderate": return <Clock className="w-3.5 h-3.5" />;
      case "low": return <CheckCircle2 className="w-3.5 h-3.5" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100/50 backdrop-blur-sm border border-amber-200/50 shadow-sm">
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            </span>
            Starvation Alerts
          </h1>
          <p className="text-sm mt-2 text-gray-500">
            Encounters waiting beyond department threshold
          </p>
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <select
              value={dept}
              onChange={(e) => setDept(e.target.value)}
              className="appearance-none pl-4 pr-10 py-2.5 rounded-xl text-sm font-semibold cursor-pointer transition-all focus:outline-none bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg text-gray-700 hover:bg-white/80"
              style={{ minWidth: 180 }}
            >
              <option value="">All Departments</option>
              {depts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:scale-105 active:scale-95 bg-white/70 backdrop-blur-xl border border-white/50 shadow-lg text-gray-700 hover:bg-white/80"
            onClick={load}
          >
            <RefreshCw className="w-4 h-4 text-blue-500" />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 gap-4 text-gray-500">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-gray-200 rounded-full" />
            <div className="absolute top-0 left-0 w-12 h-12 border-4 border-amber-500 rounded-full border-t-transparent animate-spin" />
          </div>
          <span className="text-sm font-medium tracking-widest uppercase">
            Loading alerts...
          </span>
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 rounded-3xl border border-dashed bg-gray-50/50 backdrop-blur-sm border-gray-200">
          <CheckCircle2 className="w-16 h-16 text-emerald-300 mb-4" />
          <p className="font-medium text-gray-700">No starvation alerts</p>
          <p className="text-sm mt-1 text-gray-400">All patients within SLA</p>
        </div>
      ) : (
        <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-4 shadow-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Patient</th>
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Priority</th>
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Wait</th>
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Threshold</th>
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Dept</th>
                <th className="text-left py-3 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500">Doctor</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((enc) => (
                <tr
                  key={enc.id}
                  className="border-b border-gray-100 hover:bg-white/50 transition-colors group"
                >
                  <td className="py-3 px-4 font-semibold text-gray-700">
                    {enc.patient_detail?.name || "—"}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border backdrop-blur-sm ${enc.priority === "critical"
                        ? "bg-rose-50/80 border-rose-200 text-rose-700"
                        : enc.priority === "high"
                          ? "bg-orange-50/80 border-orange-200 text-orange-700"
                          : enc.priority === "moderate"
                            ? "bg-amber-50/80 border-amber-200 text-amber-700"
                            : "bg-emerald-50/80 border-emerald-200 text-emerald-700"
                        }`}
                    >
                      {getPriorityIcon(enc.priority)}
                      {enc.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-bold text-rose-600">
                    {enc.wait_minutes}m
                  </td>
                  <td className="py-3 px-4 text-gray-500">
                    {enc.threshold_minutes}m
                  </td>
                  <td className="py-3 px-4 text-gray-500">
                    {enc.department_name ||
                      depts.find((d) => d.id === enc.department)?.name ||
                      enc.department ||
                      "—"}
                  </td>
                  <td
                    className={`py-3 px-4 font-medium ${enc.assigned_doctor_detail
                      ? "text-gray-700"
                      : "text-amber-600"
                      }`}
                  >
                    {enc.assigned_doctor_detail?.full_name || (
                      <span className="flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" /> Unassigned
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


// ─── Staff Page ────────────────────────────────────────────────
function StaffPage() {
  const [depts, setDepts] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchingLogs, setFetchingLogs] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    username: "",
    password: "",
    email: "",
    full_name: "",
    role: "doctor",
    department_id: "",
  });

  const fetchStaff = useCallback(async () => {
    setFetchingLogs(true);
    try {
      const data = await AdminAPI.staffList();
      setStaffList(Array.isArray(data) ? data : []);
    } catch {
    } finally {
      setFetchingLogs(false);
    }
  }, []);

  useEffect(() => {
    AdminAPI.departments()
      .then((d) => setDepts(Array.isArray(d) ? d : []))
      .catch(() => { });
    fetchStaff();
  }, [fetchStaff]);

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to disable this user?")) return;
    try {
      await AdminAPI.deleteStaff(id);
      setMsg({ type: "success", text: "User account disabled successfully." });
      if (editingId === id) cancelEdit();
      fetchStaff();
    } catch (err) {
      setMsg({
        type: "danger",
        text:
          "Error disabling user: " +
          (err.response?.data?.errors || err.message),
      });
    } finally {
      setTimeout(() => setMsg(null), 3000);
    }
  };

  const handleEnable = async (u) => {
    try {
      await AdminAPI.updateStaff(u.id, { is_active: true });
      setMsg({
        type: "success",
        text: `Authentication restored for ${u.full_name}.`,
      });
      fetchStaff();
    } catch (err) {
      setMsg({
        type: "danger",
        text: "Failed to restore account authorization.",
      });
    } finally {
      setTimeout(() => setMsg(null), 3000);
    }
  };

  const handleEdit = (u) => {
    setEditingId(u.id);
    setForm({
      username: u.username || u.clerk_user_id || u.id.split("-")[0],
      password: "",
      email: u.email || "",
      full_name: u.full_name || "",
      role: u.role || "doctor",
      department_id: u.department_id || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm({
      username: "",
      password: "",
      email: "",
      full_name: "",
      role: "doctor",
      department_id: "",
    });
    setMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      if (editingId) {
        const patchData = { ...form };
        if (!patchData.password) delete patchData.password;
        await AdminAPI.updateStaff(editingId, patchData);
        setMsg({
          type: "success",
          text: `Identity verified for ${form.full_name}. Profile updated.`,
        });
        cancelEdit();
      } else {
        await AuthAPI.register(form);
        setMsg({
          type: "success",
          text: `New medical record initialized for ${form.full_name}.`,
        });
        setForm({
          username: "",
          password: "",
          email: "",
          full_name: "",
          role: "doctor",
          department_id: "",
        });
      }
      fetchStaff();
    } catch (err) {
      setMsg({
        type: "danger",
        text:
          "System rejection: " + (err.response?.data?.errors || err.message),
      });
    } finally {
      setLoading(false);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  if (fetchingLogs && staffList.length === 0)
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4 text-gray-500">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-gray-200 rounded-full" />
          <div className="absolute top-0 left-0 w-12 h-12 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin" />
        </div>
        <span className="text-sm font-medium tracking-widest uppercase italic opacity-80">
          Syncing personnel directory...
        </span>
      </div>
    );

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100/50 backdrop-blur-sm border border-indigo-200/50 shadow-sm">
              <Users className="w-6 h-6 text-indigo-600" />
            </span>
            Medical Personnel
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage hospital roles, credentials, and departmental access
          </p>
        </div>
        {msg && (
          <div
            className={`px-4 py-3 rounded-xl text-xs font-black uppercase tracking-widest border animate-in zoom-in-95 duration-300 backdrop-blur-sm ${msg.type === "success"
              ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
              : "bg-rose-50/80 border-rose-200 text-rose-700"
              }`}
          >
            {msg.type === "success" ? (
              <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 inline mr-1.5" />
            )}
            {msg.text}
          </div>
        )}
      </div>

      {/* Top Section: Registration Form */}
      <div className="max-w-4xl mx-auto">
        <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-4xl p-8 shadow-2xl">
          <div className="flex items-center gap-4 mb-8">
            <div
              className={`w-12 h-12 rounded-2xl flex items-center justify-center text-xl shadow-inner backdrop-blur-sm ${editingId
                ? "bg-blue-50/80 border border-blue-200 text-blue-600"
                : "bg-emerald-50/80 border border-emerald-200 text-emerald-600"
                }`}
            >
              {editingId ? <Edit className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-lg font-black text-gray-700 uppercase tracking-tight">
                {editingId ? "Identity Calibration" : "Personnel Induction"}
              </h2>
              <p className="text-gray-500 text-xs font-bold uppercase tracking-widest">
                {editingId
                  ? `Modifying profile for UID: ${editingId.split("-")[0]}`
                  : "Assign initial credentials and role"}
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Full Legal Name
                </label>
                <input
                  className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all placeholder:text-gray-400"
                  value={form.full_name}
                  onChange={(e) =>
                    setForm({ ...form, full_name: e.target.value })
                  }
                  required
                  placeholder="e.g. Dr. Alexander Pierce"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Operational Role
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all appearance-none cursor-pointer"
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                  >
                    <option value="doctor">Medical Doctor</option>
                    <option value="nurse">Clinical Nurse</option>
                    <option value="dept_head">Department Head</option>
                    <option value="admin">System Administrator</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  System Login ID
                </label>
                <input
                  className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all placeholder:text-gray-400"
                  value={form.username}
                  onChange={(e) =>
                    setForm({ ...form, username: e.target.value })
                  }
                  placeholder="e.g. apierce_md"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  {editingId ? "Access Reset (Secret)" : "Initial Password"}
                  {editingId && (
                    <span className="ml-2 text-gray-400">(Optional)</span>
                  )}
                </label>
                <input
                  type="password"
                  className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all placeholder:text-gray-400"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  placeholder={
                    editingId ? "Leave empty to retain" : "Temporary secure key"
                  }
                  required={!editingId}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Electronic Mail
                </label>
                <input
                  type="email"
                  className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all placeholder:text-gray-400"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  placeholder="a.pierce@hospital.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                  Assigned Unit
                  {form.role === "admin" && (
                    <span className="ml-2 text-gray-400">(Optional)</span>
                  )}
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-white/80 border border-gray-200 rounded-2xl px-5 py-4 text-gray-700 focus:ring-4 focus:ring-indigo-500/20 outline-none transition-all appearance-none cursor-pointer"
                    value={form.department_id}
                    onChange={(e) =>
                      setForm({ ...form, department_id: e.target.value })
                    }
                    required={form.role === "doctor" || form.role === "nurse"}
                  >
                    <option value="">Select unit deployment...</option>
                    {depts.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                </div>
              </div>
            </div>

            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                className={`flex-1 py-4 rounded-2xl font-black text-sm uppercase tracking-[0.2em] shadow-xl transition-all active:scale-95 disabled:opacity-50 ${editingId
                  ? "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/30"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/30"
                  }`}
                disabled={loading}
              >
                {loading
                  ? "Synchronizing..."
                  : editingId
                    ? "Commit Update"
                    : "Authorize Personnel"}
              </button>
              {editingId && (
                <button
                  type="button"
                  className="px-8 bg-gray-100/50 hover:bg-gray-200/50 text-gray-600 font-bold rounded-2xl transition-all active:scale-95 uppercase text-xs tracking-widest backdrop-blur-sm"
                  onClick={cancelEdit}
                >
                  Abort
                </button>
              )}
            </div>
          </form>
        </div>
      </div>

      {/* Active Directory Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between px-2">
          <h2 className="text-xs font-black text-gray-500 uppercase tracking-[0.25em] flex items-center gap-3">
            <span className="w-1.5 h-6 bg-indigo-500 rounded-full shadow-lg" />
            Active Personnel Database
          </h2>
          <span className="px-3 py-1 bg-indigo-50/80 border border-indigo-200 rounded-full text-[10px] font-black text-indigo-700 uppercase tracking-widest backdrop-blur-sm">
            {staffList.filter((u) => u.is_active).length} Records Verified
          </span>
        </div>

        {staffList.filter((u) => u.is_active).length === 0 ? (
          <div className="bg-white/50 backdrop-blur-sm border border-white/50 rounded-3xl p-16 text-center">
            <p className="text-gray-500 italic font-medium">
              Personnel directory is currently empty...
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {staffList
              .filter((u) => u.is_active)
              .map((u) => (
                <div
                  key={u.id}
                  className="group bg-white/50 backdrop-blur-md border border-white/50 rounded-3xl p-5 hover:border-indigo-200 hover:bg-white/80 transition-all duration-500 flex flex-col justify-between shadow-lg hover:shadow-indigo-500/10"
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-white/80 border border-gray-200 flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform duration-500">
                          {u.role === "admin" ? (
                            <Shield className="w-6 h-6 text-amber-600" />
                          ) : u.role === "doctor" ? (
                            <Stethoscope className="w-6 h-6 text-blue-600" />
                          ) : u.role === "nurse" ? (
                            <HeartPulse className="w-6 h-6 text-emerald-600" />
                          ) : (
                            <User className="w-6 h-6 text-purple-600" />
                          )}
                        </div>
                        <div>
                          <h3 className="text-sm font-black text-gray-700 group-hover:text-indigo-600 transition-colors leading-tight">
                            {u.full_name}
                          </h3>
                          <p className="text-[10px] font-medium text-gray-500 font-mono tracking-tighter mt-0.5 uppercase italic">
                            {u.username || u.clerk_user_id || u.id.split("-")[0]}
                          </p>
                        </div>
                      </div>
                      <div
                        className={`px-2 py-0.5 rounded-lg border text-[10px] font-black uppercase tracking-widest backdrop-blur-sm ${u.role === "admin"
                          ? "bg-amber-50/80 border-amber-200 text-amber-700"
                          : u.role === "doctor"
                            ? "bg-blue-50/80 border-blue-200 text-blue-700"
                            : u.role === "nurse"
                              ? "bg-emerald-50/80 border-emerald-200 text-emerald-700"
                              : "bg-purple-50/80 border-purple-200 text-purple-700"
                          }`}
                      >
                        {u.role.replace("_", " ")}
                      </div>
                    </div>

                    <div className="space-y-1 pl-1">
                      <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500 truncate">
                        <Mail className="w-3 h-3" /> {u.email}
                      </div>
                      {u.department_name && (
                        <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-tight">
                          <Building2 className="w-3 h-3" /> {u.department_name}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-6 flex gap-2">
                    <button
                      className="flex-1 py-2 bg-white/80 hover:bg-indigo-600 hover:text-white text-gray-600 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-gray-200 hover:border-indigo-500 active:scale-95 backdrop-blur-sm"
                      onClick={() => handleEdit(u)}
                    >
                      Edit Profile
                    </button>
                    <button
                      className="px-4 py-2 bg-white/80 hover:bg-rose-50 text-gray-500 hover:text-rose-600 text-[10px] font-black rounded-xl transition-all border border-gray-200 hover:border-rose-200 active:scale-95 backdrop-blur-sm"
                      title="Disable Account"
                      onClick={() => handleDelete(u.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Disabled Section */}
      <div className="space-y-4 pt-10 opacity-70 border-t border-gray-200/50">
        <div className="flex items-center justify-between px-2">
          <h2 className="text-xs font-black text-gray-400 uppercase tracking-[0.25em] flex items-center gap-3">
            <span className="w-1.5 h-4 bg-gray-400 rounded-full" />
            Decommissioned Accounts
          </h2>
          <span className="text-[10px] font-bold text-gray-400 uppercase italic">
            Authorization Revoked
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {staffList.filter((u) => !u.is_active).length === 0 ? (
            <div className="col-span-full py-8 text-center bg-white/20 backdrop-blur-sm border border-white/20 rounded-3xl">
              <p className="text-gray-400 text-[10px] font-black uppercase tracking-widest">
                No restricted credentials found.
              </p>
            </div>
          ) : (
            staffList
              .filter((u) => !u.is_active)
              .map((u) => (
                <div
                  key={u.id}
                  className="group bg-white/30 backdrop-blur-sm border border-white/20 rounded-2xl p-4 flex items-center justify-between hover:border-indigo-200/50 transition-all duration-300"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-white/50 flex items-center justify-center text-sm opacity-50 group-hover:opacity-100 transition-all">
                      <User className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-gray-500 truncate group-hover:text-gray-700 transition-colors uppercase tracking-tight">
                        {u.full_name}
                      </div>
                      <div className="text-[9px] font-black text-gray-400 uppercase tracking-tighter truncate">
                        {u.role}
                      </div>
                    </div>
                  </div>
                  <button
                    className="p-2 text-[10px] font-black text-indigo-400/70 hover:text-indigo-600 uppercase border border-indigo-200/30 hover:border-indigo-300 rounded-xl bg-indigo-50/20 hover:bg-indigo-50/60 transition-all active:scale-95 backdrop-blur-sm"
                    onClick={() => handleEnable(u)}
                    title="Restore Authorization"
                  >
                    Restore
                  </button>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Simulation Page ──────────────────────────────────────────
const SCENARIOS = [
  {
    id: "cardiac_surge",
    label: "Cardiac Surge",
    desc: "30 patients flooding ER with cardiac symptoms — tachycardia, chest pain, low SpO₂",
    icon: HeartPulse,
    color: "rose",
    gradient: "from-rose-500 to-pink-500",
    bgLight: "bg-rose-50/80",
    borderLight: "border-rose-200",
    textColor: "text-rose-600",
  },
  {
    id: "mass_casualty",
    label: "Mass Casualty Event",
    desc: "Multi-trauma victims from an accident scene — head injuries, fractures, hemorrhage",
    icon: AlertTriangle,
    color: "orange",
    gradient: "from-orange-500 to-amber-500",
    bgLight: "bg-orange-50/80",
    borderLight: "border-orange-200",
    textColor: "text-orange-600",
  },
  {
    id: "pneumonia_cluster",
    label: "Pneumonia Cluster",
    desc: "Respiratory outbreak — low SpO₂, fever, elevated RR, vulnerable patients",
    icon: FlaskConical,
    color: "blue",
    gradient: "from-blue-500 to-indigo-500",
    bgLight: "bg-blue-50/80",
    borderLight: "border-blue-200",
    textColor: "text-blue-600",
  },
  {
    id: "normal_ops",
    label: "Normal Operations",
    desc: "Standard ER day — mix of low/moderate severity to test baseline queue handling",
    icon: Activity,
    color: "emerald",
    gradient: "from-emerald-500 to-green-500",
    bgLight: "bg-emerald-50/80",
    borderLight: "border-emerald-200",
    textColor: "text-emerald-600",
  },
];

function SimulationPage() {
  const [scenario, setScenario] = useState("cardiac_surge");
  const [patientCount, setPatientCount] = useState(20);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [animCount, setAnimCount] = useState(0);

  const runSim = async () => {
    setRunning(true);
    setResult(null);
    setError(null);
    setAnimCount(0);
    try {
      const data = await SimulateAPI.run({
        scenario,
        patient_count: patientCount,
      });
      // Animate counter
      const total = data.patients_created || patientCount;
      let i = 0;
      const tick = setInterval(() => {
        i = Math.min(i + Math.ceil(total / 20), total);
        setAnimCount(i);
        if (i >= total) clearInterval(tick);
      }, 60);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.message || "Simulation failed");
    } finally {
      setRunning(false);
    }
  };

  const selectedScenario = SCENARIOS.find((s) => s.id === scenario);
  const ScenarioIcon = selectedScenario?.icon || Rocket;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100/50 backdrop-blur-sm border border-indigo-200/50 shadow-sm">
              <Rocket className="w-6 h-6 text-indigo-600" />
            </span>
            Live ER Simulation
          </h1>
          <p className="text-gray-500 text-sm mt-1.5">
            Flood the system with simulated patients. Watch AI triage in action.
          </p>
        </div>
        {result && (
          <div className="px-4 py-2 bg-emerald-50/80 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-black uppercase tracking-widest animate-in zoom-in-95 backdrop-blur-sm">
            <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5" />
            Simulation Complete
          </div>
        )}
      </div>

      {/* Scenario Selection */}
      <div>
        <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-4 pl-1">
          Select Scenario
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {SCENARIOS.map((s) => {
            const Icon = s.icon;
            const isSelected = scenario === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setScenario(s.id)}
                className={`group relative overflow-hidden backdrop-blur-xl transition-all duration-300 rounded-2xl p-6 text-left border-2 cursor-pointer shadow-lg ${isSelected
                  ? `scale-[1.02] border-${s.color}-300 bg-gradient-to-br ${s.bgLight}`
                  : "border-white/50 bg-white/70 hover:bg-white/80 hover:border-gray-200"
                  }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-xl ${s.bgLight} border ${s.borderLight} backdrop-blur-sm group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className={`w-5 h-5 ${s.textColor}`} />
                  </div>
                  <div>
                    <div className={`font-black text-base mb-1 ${isSelected ? s.textColor : "text-gray-700"}`}>
                      {s.label}
                    </div>
                    <div className={`text-sm font-medium leading-relaxed ${isSelected ? "text-gray-600" : "text-gray-500"}`}>
                      {s.desc}
                    </div>
                  </div>
                </div>
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <span className="relative flex h-3 w-3">
                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full bg-${s.color}-400 opacity-75`}></span>
                      <span className={`relative inline-flex rounded-full h-3 w-3 bg-${s.color}-500`}></span>
                    </span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-6 bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-8 shadow-xl mt-10">
        <div>
          <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-4 pl-1">
            Simulation Magnitude
          </div>
          <div className="flex items-center gap-4">
            {[10, 20, 30, 50].map((n) => (
              <button
                key={n}
                onClick={() => setPatientCount(n)}
                className={`w-14 h-14 rounded-2xl font-black transition-all active:scale-90 flex items-center justify-center ${patientCount === n
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/30"
                  : "bg-white/80 text-gray-600 border border-gray-200 hover:border-indigo-200 hover:text-indigo-600 backdrop-blur-sm"
                  }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={runSim}
          disabled={running}
          className={`px-10 py-5 rounded-2xl font-black text-lg tracking-widest shadow-2xl transition-all active:scale-95 flex items-center gap-4 ${running ? "opacity-50 cursor-not-allowed bg-gray-200" : "cursor-pointer hover:translate-y-[-2px]"
            }`}
          style={{
            background: running
              ? "#e5e7eb"
              : `linear-gradient(135deg, ${selectedScenario?.color === "rose" ? "#f43f5e" : selectedScenario?.color === "orange" ? "#f97316" : selectedScenario?.color === "blue" ? "#3b82f6" : "#10b981"}, #6366f1)`,
            color: "#fff",
            boxShadow: running ? "none" : `0 15px 35px -5px ${selectedScenario?.color === "rose" ? "#f43f5e" : selectedScenario?.color === "orange" ? "#f97316" : selectedScenario?.color === "blue" ? "#3b82f6" : "#10b981"}66`,
          }}
        >
          {running ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              Simulating...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              LAUNCH SIMULATION
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="bg-rose-50/80 border border-rose-200 rounded-2xl p-4 text-rose-700 font-semibold backdrop-blur-sm">
          <AlertCircle className="w-4 h-4 inline mr-2" />
          {error}
        </div>
      )}

      {/* Live counter */}
      {running && (
        <div className="flex flex-col items-center justify-center py-20 bg-white/70 backdrop-blur-xl border border-white/50 rounded-[2.5rem] shadow-xl animate-pulse">
          <div className="text-xs font-black text-gray-500 uppercase tracking-[0.3em] mb-4">
            Injecting Patients into ER
          </div>
          <div
            className="text-9xl font-black text-indigo-600 tracking-tighter"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {animCount}
          </div>
          <div className="text-gray-500 text-lg font-bold mt-4 uppercase tracking-widest">patients processed</div>
          <div className="mt-10 w-64 h-3 bg-indigo-50 rounded-full overflow-hidden border border-indigo-100">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full transition-all duration-300 shadow-lg"
              style={{
                width: `${Math.min((animCount / patientCount) * 100, 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Results */}
      {result && !running && (
        <div className="space-y-10 animate-in fade-in slide-in-from-bottom-10 duration-700">
          <div className="text-xs font-black text-gray-500 uppercase tracking-[0.2em] flex items-center gap-4">
            <span className="h-px bg-gray-200 flex-1" />
            Simulation Outcomes
            <span className="h-px bg-gray-200 flex-1" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              {
                label: "Patients Created",
                value: result.patients_created,
                icon: Users,
                color: "text-blue-600",
                bg: "bg-blue-50",
              },
              {
                label: "Auto-Assigned",
                value: result.auto_assigned,
                icon: CheckCircle2,
                color: "text-emerald-600",
                bg: "bg-emerald-50",
              },
              {
                label: "Escalations",
                value: result.escalations_triggered,
                icon: AlertTriangle,
                color: "text-rose-600",
                bg: "bg-rose-50",
              },
              {
                label: "Unassigned",
                value: result.patients_created - result.auto_assigned,
                icon: AlertCircle,
                color: "text-amber-600",
                bg: "bg-amber-50",
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.label}
                  className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-8 text-center shadow-lg hover:translate-y-[-5px] transition-transform duration-300"
                >
                  <div className={`text-4xl mb-4 w-16 h-16 ${s.bg} rounded-2xl flex items-center justify-center mx-auto shadow-inner`}>
                    <Icon className={`w-8 h-8 ${s.color}`} />
                  </div>
                  <div className={`text-5xl font-black ${s.color} tracking-tighter`}>
                    {s.value ?? 0}
                  </div>
                  <div className="text-xs font-black text-gray-500 uppercase tracking-widest mt-3">
                    {s.label}
                  </div>
                </div>
              );
            })}
          </div>
          {result.priority_breakdown && (
            <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-[2rem] p-8 shadow-lg">
              <div className="text-xs font-black text-gray-500 uppercase tracking-widest mb-6 pl-1">
                Clinical Priority Distribution
              </div>
              <div className="flex gap-4 flex-wrap">
                {Object.entries(result.priority_breakdown).map(([p, count]) => (
                  <div
                    key={p}
                    className={`flex items-center gap-4 px-6 py-3 rounded-2xl border-2 bg-white/80 backdrop-blur-sm ${p === "critical"
                      ? "border-rose-200 text-rose-700"
                      : p === "high"
                        ? "border-orange-200 text-orange-700"
                        : p === "moderate"
                          ? "border-amber-200 text-amber-700"
                          : "border-emerald-200 text-emerald-700"
                      }`}
                  >
                    <span className="font-black text-2xl">{count}</span>
                    <span className="text-xs font-black uppercase tracking-widest opacity-80">
                      {p}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="bg-indigo-50/50 border border-indigo-200 rounded-2xl p-6 text-center backdrop-blur-sm">
            <p className="text-gray-600 text-sm font-bold uppercase tracking-wide">
              Go to <strong className="text-indigo-600">ED Queue</strong> (Nurse view) to see all {result.patients_created} patients sorted by AI triage priority in real-time.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Operational AI Insight Assistant ──────────────────────────
function HospitalAiAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [msgs, loading]);

  const renderMessageText = (text) => {
    if (!text) return null;
    return text.split("\n").map((line, i) => {
      let cleanLine = line.trim();
      let isBullet = false;

      if (cleanLine.startsWith("* ")) {
        isBullet = true;
        cleanLine = cleanLine.substring(2);
      }

      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const formatted = parts.map((part, idx) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={idx} className="font-black text-indigo-900">{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      return (
        <div key={i} className={`flex gap-2 ${isBullet ? "ml-1" : ""} ${line.trim() === "" ? "h-2" : ""}`}>
          {isBullet && <span className="text-indigo-500 font-bold shrink-0">•</span>}
          <div className="flex-1">{formatted}</div>
        </div>
      );
    });
  };

  const fetchInsight = async (
    userText = "Give me a quick summary of the current hospital situation.",
    isUserMessage = false,
  ) => {
    setLoading(true);
    if (isUserMessage) {
      setMsgs((prev) => [...prev, { role: "user", text: userText }]);
    }

    try {
      const [overview, starvation] = await Promise.all([
        AdminAPI.overview().catch(() => ({})),
        AdminAPI.starvationAlerts().catch(() => []),
      ]);
      const contextStr = JSON.stringify({
        active_patients: overview?.active_patients || 0,
        starving_cases: Array.isArray(starvation) ? starvation.length : 0,
        avg_wait_minutes: overview?.avg_wait_minutes || 0,
        queue_load: overview?.queue_load || "Normal",
        doctor_utilization: overview?.doctor_utilization_pct || 0,
        critical_cases: overview?.priority_distribution?.critical || 0,
      });

      const res = await AdminAPI.insightChat({
        prompt: userText,
        context: contextStr,
      });
      setMsgs((prev) => [...prev, { role: "ai", text: res.answer }]);
    } catch {
      setMsgs((prev) => [
        ...prev,
        { role: "ai", text: "⚠️ Unable to reach the intelligence layer." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && !started) {
      setStarted(true);
      fetchInsight(
        "Give me a quick summary of the current hospital situation.",
        false,
      );
    }
  }, [isOpen, started]);

  const sendMsg = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    await fetchInsight(userText, true);
  };

  return (
    <div className="fixed bottom-8 right-8 z-50">
      {isOpen ? (
        <div className="w-[380px] h-[500px] bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl flex flex-col overflow-hidden shadow-2xl animate-in slide-in-from-bottom-5 duration-300">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 p-4 flex justify-between items-center">
            <div className="flex items-center gap-2 text-white font-bold">
              <Bot size={20} /> Operations AI
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10"
            >
              <X size={20} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 bg-gray-50/50">
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] p-3 text-sm rounded-2xl shadow-sm ${m.role === "user"
                  ? "self-end bg-indigo-600 text-white rounded-br-none"
                  : "self-start bg-white border border-gray-200 text-gray-700 rounded-bl-none"
                  }`}
              >
                {renderMessageText(m.text)}
              </div>
            ))}
            {loading && (
              <div className="self-start flex gap-1 p-3">
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={sendMsg} className="flex border-t border-gray-200 bg-white/80 backdrop-blur-sm p-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about hospital metrics..."
              className="flex-1 px-4 py-2 bg-transparent text-gray-700 outline-none placeholder:text-gray-400"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className={`p-2 rounded-xl transition-all ${input.trim() && !loading
                ? "text-indigo-600 hover:bg-indigo-50"
                : "text-gray-300 cursor-not-allowed"
                }`}
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-700 text-white flex items-center justify-center border-2 border-white/20 shadow-xl hover:scale-105 transition-transform duration-200"
        >
          <MessageSquare size={24} />
        </button>
      )}
    </div>
  );
}

export default function AdminDashboard() {
  return (
    <Shell>
      <Routes>
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="starvation" element={<StarvationPage />} />
        <Route path="forecast" element={<ForecastPage />} />
        <Route path="simulate" element={<SimulationPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="staff" element={<StaffPage />} />
      </Routes>
      <HospitalAiAssistant />
    </Shell>
  );
}

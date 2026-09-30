import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { AuthAPI } from "../api/client";
import {
  Stethoscope,
  HeartPulse,
  Settings,
  Activity,
  AlertCircle,
} from "lucide-react";

export default function LoginPage() {
  const { setToken, fetchUser, isLoading, user } = useAuthStore();
  const navigate = useNavigate();
  const [mode, setMode] = useState("doctor");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // Only redirect if there is a user AND we aren't actively loading them
  if (user && !isLoading) {
    return <Navigate to="/" replace />;
  }

  const handleStaffLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Enter username and password");
      return;
    }
    setError("");
    console.log("[LoginPage] Attempting login for:", username);
    try {
      const { token } = await AuthAPI.login({
        username: username.trim(),
        password,
      });
      console.log("[LoginPage] Token received:", token ? "Yes" : "No");
      setToken(token);
      console.log("[LoginPage] Fetching user profile...");
      await fetchUser();
      console.log("[LoginPage] Done fetching user, current local state");
    } catch (err) {
      console.error("[LoginPage] Login failed, error:", err);
      console.error("[LoginPage] Error response:", err.response?.data);
      setError(err.response?.data?.errors?.[0] || "Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 relative overflow-hidden font-sans">
      {/* Medical-themed background pattern: faint EKG line and dots */}
      <div className="absolute inset-0 opacity-[0.15] pointer-events-none">
        <div
          className="absolute top-0 left-0 w-full h-full"
          style={{
            backgroundImage: `
                             radial-gradient(circle at 20px 20px, #3b82f6 1px, transparent 1px),
                             radial-gradient(circle at 80px 150px, #10b981 1px, transparent 1px),
                             repeating-linear-gradient(45deg, transparent, transparent 20px, rgba(59,130,246,0.03) 20px, rgba(59,130,246,0.03) 40px)
                         `,
            backgroundSize: "40px 40px, 100px 100px, 80px 80px",
          }}
        />
        {/* EKG line decoration */}
        <svg
          className="absolute bottom-0 left-0 w-full h-32 opacity-20"
          viewBox="0 0 1200 120"
          preserveAspectRatio="none"
        >
          <path
            d="M0,60 L200,60 L250,20 L300,100 L350,40 L400,80 L450,60 L500,60 L550,60 L600,60 L650,60 L700,60 L750,60 L800,60 L850,60 L900,60 L950,60 L1000,60 L1050,60 L1100,60 L1150,60 L1200,60"
            stroke="#3b82f6"
            strokeWidth="2"
            fill="none"
            strokeDasharray="5 5"
          />
        </svg>
      </div>

      {/* Soft gradient orbs for depth */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-200/30 rounded-full blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-200/30 rounded-full blur-[120px]" />

      <div className="w-full max-w-md p-6 relative z-10">
        {/* Logo & Header */}
        <div className="text-center mb-8 transform transition-all duration-700">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/70 backdrop-blur-xl rounded-2xl mb-4 border border-white/50 shadow-xl group">
            <img
              src="/logo.svg"
              alt="Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <h1 className="text-4xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent tracking-tighter">
            Acuvera
          </h1>
          <p className="text-gray-500 text-sm font-medium mt-1 tracking-wide uppercase">
            Emergency Department Intelligence
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-8 shadow-xl">
          {/* Role Selection Tabs */}
          <div className="flex p-1 bg-white/50 rounded-xl mb-8 border border-white/30">
            <button
              onClick={() => setMode("doctor")}
              className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center justify-center gap-1.5 ${
                mode === "doctor"
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30 ring-1 ring-blue-500/50"
                  : "text-gray-500 hover:text-gray-700 bg-transparent hover:bg-white/50"
              }`}
            >
              <Stethoscope size={16} />
              Doctor
            </button>
            <button
              onClick={() => setMode("nurse")}
              className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center justify-center gap-1.5 ${
                mode === "nurse"
                  ? "bg-rose-600 text-white shadow-lg shadow-rose-600/30 ring-1 ring-rose-500/50"
                  : "text-gray-500 hover:text-gray-700 bg-transparent hover:bg-white/50"
              }`}
            >
              <HeartPulse size={16} />
              Nurse
            </button>
            <button
              onClick={() => setMode("admin")}
              className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center justify-center gap-1.5 ${
                mode === "admin"
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30 ring-1 ring-violet-500/50"
                  : "text-gray-500 hover:text-gray-700 bg-transparent hover:bg-white/50"
              }`}
            >
              <Settings size={16} />
              Admin
            </button>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <span
                className={`w-1.5 h-6 rounded-full ${
                  mode === "doctor"
                    ? "bg-blue-500"
                    : mode === "nurse"
                      ? "bg-rose-500"
                      : "bg-violet-500"
                }`}
              />
              {mode.charAt(0).toUpperCase() + mode.slice(1)} Portal
            </h2>
            <p className="text-gray-500 text-xs mt-1">
              Access secure clinical workspace
            </p>
          </div>

          <form onSubmit={handleStaffLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">
                Clinical ID
              </label>
              <input
                className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter assigned username"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">
                Secure Key
              </label>
              <input
                type="password"
                className="w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-rose-50/80 border border-rose-200 text-rose-700 text-xs py-3 px-4 rounded-xl flex items-center gap-2 animate-shake backdrop-blur-sm">
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <button
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-500/30 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Activity size={18} />
                  Authorize Access
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer Info */}
        <div className="mt-8 space-y-4 text-center">
          <p className="text-gray-400 text-[10px] items-center justify-center gap-2 uppercase tracking-[0.2em] font-bold">
            Acuvera <span className="text-blue-600 font-extrabold">v0.1</span> •
            India Optimized • PWA Ready
          </p>

          <div className="p-4 bg-white/50 backdrop-blur-md rounded-2xl border border-white/30 shadow-sm">
            <p className="text-[10px] text-gray-500 leading-relaxed font-medium">
              <span className="text-amber-600/80 font-bold block mb-1 uppercase tracking-wider flex items-center gap-1 justify-center">
                <AlertCircle size={12} /> Clinical Decision Support Disclaimer
              </span>
              Acuvera triage prioritization is a digital tool to assist staff.
              Diagnostic responsibility remains with qualified healthcare
              professionals. Privacy-first: No sensitive PHI is processed by
              external AI.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

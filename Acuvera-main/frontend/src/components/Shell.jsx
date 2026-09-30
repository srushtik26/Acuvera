import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import {
  LayoutDashboard,
  ClipboardList,
  Siren,
  BarChart2,
  AlertTriangle,
  TrendingUp,
  Settings,
  Users,
  LogOut,
  Activity,
  Stethoscope,
  ChevronRight,
  Zap,
  History,
} from "lucide-react";

const NAV = {
  nurse: [
    {
      path: "/nurse/queue",
      icon: Siren,
      label: "ED Queue",
      color: "text-rose-600",
      bg: "bg-rose-50",
      border: "border-rose-200",
    },
    {
      path: "/nurse/escalations",
      icon: AlertTriangle,
      label: "Escalations",
      color: "text-amber-600",
      bg: "bg-amber-50",
      border: "border-amber-200",
    },
  ],
  doctor: [
    {
      path: "/doctor/my-cases",
      icon: LayoutDashboard,
      label: "My Cases",
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
    },
    {
      path: "/doctor/assignments",
      icon: ClipboardList,
      label: "Assignments",
      color: "text-indigo-600",
      bg: "bg-indigo-50",
      border: "border-indigo-200",
    },
    {
      path: "/doctor/history",
      icon: History,
      label: "Patient History",
      color: "text-slate-600",
      bg: "bg-slate-50",
      border: "border-slate-200",
    },
  ],
  admin: [
    {
      path: "/admin/overview",
      icon: BarChart2,
      label: "Overview",
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
    },
    {
      path: "/admin/starvation",
      icon: AlertTriangle,
      label: "Starvation",
      color: "text-amber-600",
      bg: "bg-amber-50",
      border: "border-amber-200",
    },
    {
      path: "/admin/forecast",
      icon: TrendingUp,
      label: "Forecast",
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      border: "border-emerald-200",
    },
    {
      path: "/admin/simulate",
      icon: Zap,
      label: "Live Simulate",
      color: "text-violet-600",
      bg: "bg-violet-50",
      border: "border-violet-200",
    },
    {
      path: "/admin/config",
      icon: Settings,
      label: "Config",
      color: "text-slate-600",
      bg: "bg-slate-50",
      border: "border-slate-200",
    },
    {
      path: "/admin/staff",
      icon: Users,
      label: "Staff",
      color: "text-indigo-600",
      bg: "bg-indigo-50",
      border: "border-indigo-200",
    },
  ],
  dept_head: [
    {
      path: "/admin/overview",
      icon: BarChart2,
      label: "Overview",
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
    },
    {
      path: "/admin/forecast",
      icon: TrendingUp,
      label: "Forecast",
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      border: "border-emerald-200",
    },
  ],
};

const ROLE_CONFIG = {
  nurse: {
    label: "Registered Nurse",
    color: "text-rose-600",
    bg: "bg-rose-50",
    border: "border-rose-200",
    icon: Stethoscope,
  },
  doctor: {
    label: "Physician",
    color: "text-blue-600",
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: Activity,
  },
  admin: {
    label: "Administrator",
    color: "text-violet-600",
    bg: "bg-violet-50",
    border: "border-violet-200",
    icon: Settings,
  },
  dept_head: {
    label: "Department Head",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    icon: BarChart2,
  },
};

export default function Shell({ children }) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const navItems = NAV[user?.role] || [];
  const roleConf = ROLE_CONFIG[user?.role] || ROLE_CONFIG.admin;
  const RoleIcon = roleConf.icon;

  const handleLogout = async () => {
    logout();
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Glassmorphic Sidebar */}
      <aside className="fixed left-0 top-0 bottom-0 w-60 bg-white/70 backdrop-blur-xl border-r border-white/50 shadow-xl z-50 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-6 border-b border-white/20">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl">
              <img
                src="/logo.svg"
                alt="Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <div className="font-black text-lg text-gray-800 tracking-tight">
                Acuvera
              </div>
              <div className="text-xs font-bold text-gray-500 tracking-widest uppercase">
                Clinical Suite
              </div>
            </div>
          </div>
        </div>

        {/* Nav Label */}
        <div className="px-5 pt-5 pb-2">
          <span className="text-xs font-black text-gray-500 tracking-widest uppercase">
            Navigation
          </span>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 px-3 flex flex-col gap-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all text-left w-full group ${
                  isActive
                    ? `bg-gradient-to-r ${item.bg} border ${item.border} text-gray-900 shadow-sm`
                    : "text-gray-500 hover:bg-white/80 hover:text-gray-700 border border-transparent"
                }`}
              >
                {/* Persistent left bar - gray for inactive, colored for active */}
                <span
                  className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full transition-colors ${
                    isActive ? item.color.replace("text", "bg") : "bg-gray-200"
                  }`}
                />
                <Icon
                  size={18}
                  className={`flex-shrink-0 ${isActive ? item.color : "text-gray-400"}`}
                />
                <span className="text-sm font-medium">{item.label}</span>
                {isActive && (
                  <ChevronRight size={14} className={`ml-auto ${item.color}`} />
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Section */}
        <div className="p-3 border-t border-white/20 space-y-3">
          {/* User Chip */}
          <div
            className={`px-4 py-3 rounded-xl border backdrop-blur-sm ${roleConf.bg} ${roleConf.border} shadow-sm`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-lg ${roleConf.bg} border ${roleConf.border} flex-shrink-0`}
              >
                <RoleIcon size={16} className={roleConf.color} />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-sm text-gray-800 truncate">
                  {user?.full_name || user?.email || "User"}
                </div>
                <div className="text-xs font-medium text-gray-500 uppercase tracking-tight">
                  {roleConf.label}
                </div>
              </div>
            </div>
          </div>

          {/* Sign Out Button */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border border-transparent text-gray-500 font-medium text-sm hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 transition-all group"
          >
            <LogOut size={16} className="group-hover:text-rose-600" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto ml-60 bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
}

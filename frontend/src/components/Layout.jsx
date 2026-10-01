import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LogOut, AlertTriangle, LayoutDashboard, ListTodo, Scale, Settings } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmtCredits } from "@/lib/format";

const NAV = [
  { to: "/", label: "Panel", icon: LayoutDashboard, id: "nav-panel" },
  { to: "/registro", label: "Registro", icon: ListTodo, id: "nav-registro" },
  { to: "/cuadrar", label: "Cuadrar", icon: Scale, id: "nav-cuadrar" },
  { to: "/ajustes", label: "Ajustes", icon: Settings, id: "nav-ajustes", admin: true },
];

export function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const { data: budget } = useQuery({ queryKey: ["budget"], queryFn: () => api.get("/cronos/budget").then((r) => r.data) });
  const warn = budget?.pct != null && budget.pct >= 80;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border bg-[#0D131F]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-[1500px] items-center gap-3 px-3 sm:gap-6 sm:px-6">
          <div className="flex items-center gap-2.5" data-testid="app-logo">
            <span className="led inline-block h-2 w-2 rounded-full bg-mint" />
            <span className="hidden font-display text-base font-bold tracking-tight xs:inline sm:inline">Cronos</span>
            <span className="mono-label hidden sm:inline">Disruptivos</span>
          </div>
          <nav className="flex items-center gap-0.5 sm:gap-1">
            {NAV.filter((n) => !n.admin || isAdmin).map(({ to, label, icon: Icon, id }) => (
              <NavLink
                key={to}
                to={to}
                end
                data-testid={id}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm font-medium transition-colors sm:px-3 ${
                    isActive ? "bg-mint/10 text-mint" : "text-slate-400 hover:bg-surface-subtle hover:text-slate-100"
                  }`
                }
              >
                <Icon size={15} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <span
              data-testid="user-role-badge"
              className={`hidden rounded-full border px-2 py-0.5 font-mono text-[11px] uppercase sm:inline ${
                isAdmin ? "border-mint/40 bg-mint/10 text-mint" : "border-border bg-surface-subtle text-slate-400"
              }`}
            >
              {user.role}
            </span>
            <span className="hidden font-mono text-xs text-slate-400 md:inline" data-testid="user-email">
              {user.email}
            </span>
            {user.picture && <img src={user.picture} alt="" className="h-7 w-7 rounded-full border border-border" />}
            <button
              data-testid="logout-button"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              className="btn-ghost"
              title="Cerrar sesión"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
        {warn && (
          <div
            data-testid="budget-warning-alert"
            className={`border-t px-4 py-2 text-center font-mono text-xs sm:px-6 ${
              budget.pct >= 100 ? "border-red-500/40 bg-red-500/10 text-red-300" : "border-amber-500/40 bg-amber-500/10 text-amber-300"
            }`}
          >
            <AlertTriangle size={13} className="mr-1.5 inline -translate-y-px" />
            Presupuesto mensual al {budget.pct}% · {fmtCredits(budget.consumed)} / {fmtCredits(budget.budget)} créditos ·
            proyección fin de mes {fmtCredits(budget.projection)} cr
          </div>
        )}
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}

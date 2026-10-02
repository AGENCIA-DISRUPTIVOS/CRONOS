import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { fmtCredits, fmtDate, fmtEur, fmtHours } from "@/lib/format";

export default function Equipo() {
  const navigate = useNavigate();
  const { data: users = [], isLoading } = useQuery({ queryKey: ["users"], queryFn: () => api.get("/cronos/users").then((r) => r.data) });
  const totals = users.reduce((a, u) => ({ credits: a.credits + u.credits, minutes: a.minutes + u.minutes, count: a.count + u.count }), { credits: 0, minutes: 0, count: 0 });
  const max = Math.max(...users.map((u) => u.credits), 1);

  return (
    <div className="space-y-4" data-testid="equipo-page">
      <div>
        <div className="mono-label">Equipo</div>
        <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Consumo por usuario</h1>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[["Usuarios", users.length, "kpi-users-count"], ["Créditos", fmtCredits(totals.credits), "kpi-users-credits"], ["Horas", fmtHours(totals.minutes), "kpi-users-hours"]].map(([l, v, id]) => (
          <div key={id} className="panel p-4" data-testid={id}>
            <div className="mono-label">{l}</div>
            <div className="mt-1 font-mono text-2xl font-bold text-mint">{v}</div>
          </div>
        ))}
      </div>
      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[1000px]" data-testid="users-table">
          <thead>
            <tr><th className="th">Usuario</th><th className="th">Rol</th><th className="th w-1/4">Créditos</th><th className="th text-right">€</th><th className="th text-right">Horas</th><th className="th text-right">Tareas</th><th className="th text-right">Mensajes</th><th className="th text-right">Este mes</th><th className="th">Modelo más usado</th><th className="th">Última actividad</th></tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="td font-mono text-xs text-slate-500" colSpan={10}>cargando…</td></tr>}
            {users.map((u) => (
              <tr key={u.email} className="cursor-pointer hover:bg-surface-subtle/60" data-testid={`user-row-${u.email}`} onClick={() => navigate(`/registro?user=${encodeURIComponent(u.email)}`)}>
                <td className="td">
                  <div className="flex items-center gap-2">
                    {u.picture ? <img src={u.picture} alt="" className="h-6 w-6 rounded-full border border-border" /> : <span className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-subtle font-mono text-[10px] uppercase text-slate-400">{u.email.slice(0, 2)}</span>}
                    <div><div className="text-sm text-slate-100">{u.name || u.email.split("@")[0]}</div><div className="font-mono text-[11px] text-slate-500">{u.email}</div></div>
                  </div>
                </td>
                <td className="td"><span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase ${u.role === "admin" ? "border-mint/40 text-mint" : "border-border text-slate-400"}`}>{u.role}</span></td>
                <td className="td">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 rounded-full bg-surface-subtle"><div className="h-full rounded-full bg-mint" style={{ width: `${(u.credits / max) * 100}%` }} /></div>
                    <span className="w-16 text-right font-mono text-sm font-semibold text-mint">{fmtCredits(u.credits)}</span>
                  </div>
                </td>
                <td className="td text-right font-mono text-xs">{fmtEur(u.cost_eur)}</td>
                <td className="td text-right font-mono text-xs">{fmtHours(u.minutes)}</td>
                <td className="td text-right font-mono text-xs">{u.count}</td>
                <td className="td text-right font-mono text-xs">{u.messages}</td>
                <td className="td text-right font-mono text-xs">{fmtCredits(u.credits_month)} cr · {fmtHours(u.minutes_month)}</td>
                <td className="td font-mono text-[11px] text-slate-300">{u.top_model || "—"}</td>
                <td className="td font-mono text-[11px] text-slate-500">{u.last_activity ? fmtDate(u.last_activity) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

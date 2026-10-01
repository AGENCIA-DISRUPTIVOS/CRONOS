import { fmtCredits, fmtEur, fmtNum } from "@/lib/format";

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const label = (ym) => `${MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;

export function MonthlyTrend({ monthly }) {
  const max = Math.max(...monthly.map((m) => m.credits), 1);
  return (
    <div className="panel overflow-x-auto" data-testid="monthly-trend">
      <div className="mono-label p-4 pb-2">Comparativa mensual</div>
      {monthly.length === 0 ? (
        <div className="px-4 pb-4 font-mono text-xs text-slate-600">sin datos</div>
      ) : (
        <table className="w-full min-w-[720px]">
          <thead>
            <tr><th className="th">Mes</th><th className="th w-1/3">Créditos</th><th className="th text-right">Δ mes ant.</th><th className="th text-right">Horas</th><th className="th text-right">Tareas</th><th className="th text-right">Mensajes</th><th className="th text-right">Coste</th></tr>
          </thead>
          <tbody>
            {monthly.map((m) => (
              <tr key={m.month} className="hover:bg-surface-subtle/60" data-testid={`monthly-row-${m.month}`}>
                <td className="td font-mono text-sm capitalize">{label(m.month)}</td>
                <td className="td">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 rounded-full bg-surface-subtle"><div className="h-full rounded-full bg-mint transition-[width] duration-500" style={{ width: `${(m.credits / max) * 100}%` }} /></div>
                    <span className="w-20 text-right font-mono text-sm font-semibold text-mint">{fmtCredits(m.credits)}</span>
                  </div>
                </td>
                <td className={`td text-right font-mono text-xs ${m.delta_pct == null ? "text-slate-600" : m.delta_pct > 0 ? "text-red-400" : "text-emerald-400"}`} data-testid={`monthly-delta-${m.month}`}>
                  {m.delta_pct == null ? "—" : `${m.delta_pct > 0 ? "+" : ""}${fmtNum(m.delta_pct, 1)}%`}
                </td>
                <td className="td text-right font-mono text-xs">{fmtNum(m.hours, 1)} h</td>
                <td className="td text-right font-mono text-xs">{m.count}</td>
                <td className="td text-right font-mono text-xs">{m.messages}</td>
                <td className="td text-right font-mono text-xs text-slate-300">{fmtEur(m.cost_eur)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

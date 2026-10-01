import { fmtCredits, fmtEur } from "@/lib/format";

export function BudgetBar({ budget }) {
  if (!budget) return null;
  const pct = budget.pct ?? 0;
  const color = pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-amber-400" : "bg-mint";
  const proj = Math.min(budget.projection_pct ?? 0, 100);
  return (
    <div className="panel p-4" data-testid="budget-panel">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="mono-label">Presupuesto mensual · {budget.month}</div>
          <div className="mt-1 font-mono text-xl font-bold">
            <span className="text-mint" data-testid="budget-consumed">{fmtCredits(budget.consumed)}</span>
            <span className="text-slate-500"> / {budget.budget ? fmtCredits(budget.budget) : "—"} cr</span>
            <span className="ml-2 text-sm text-slate-400">({fmtEur(budget.consumed_eur)})</span>
          </div>
        </div>
        <div className="text-right font-mono text-xs text-slate-400">
          <div data-testid="budget-pct">{budget.pct != null ? `${budget.pct}% consumido` : "Sin presupuesto"}</div>
          <div data-testid="budget-projection">
            Proyección: {fmtCredits(budget.projection)} cr
            {budget.projection_pct != null && <span className={budget.projection_pct > 100 ? "text-red-400" : ""}> · {budget.projection_pct}%</span>}
          </div>
          <div className="text-slate-600">día {budget.days_elapsed} de {budget.days_in_month}</div>
        </div>
      </div>
      <div className="relative mt-3 h-2.5 overflow-hidden rounded-full bg-surface-subtle" data-testid="budget-progress-bar">
        <div className="absolute inset-y-0 left-0 rounded-full bg-slate-600/40 transition-[width] duration-700" style={{ width: `${proj}%` }} />
        <div className={`absolute inset-y-0 left-0 rounded-full ${color} transition-[width] duration-700`} style={{ width: `${Math.min(pct, 100)}%` }} />
        <div className="absolute inset-y-0 w-px bg-amber-400/70" style={{ left: "80%" }} />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-slate-600">
        <span>0</span><span>aviso 80%</span><span>100%</span>
      </div>
    </div>
  );
}

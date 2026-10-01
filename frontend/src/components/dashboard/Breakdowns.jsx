import { fmtCredits, fmtEur, fmtNum, PHASE_COLORS, TYPE_COLORS } from "@/lib/format";

function Bars({ title, rows, colorFor, testId, goals }) {
  const max = Math.max(...rows.map((r) => Math.max(r.credits, goals?.[r.key] || 0)), 1);
  return (
    <div className="panel p-4" data-testid={testId}>
      <div className="mono-label mb-3">{title}</div>
      {rows.length === 0 && <div className="font-mono text-xs text-slate-600">sin datos</div>}
      <div className="space-y-2.5">
        {rows.map((r, i) => {
          const goal = goals?.[r.key];
          const over = goal != null && r.credits > goal;
          return (
            <div key={r.key} data-testid={`${testId}-row-${r.key}`} className={over ? "rounded-md bg-red-500/10 px-1.5 py-1 -mx-1.5" : ""}>
              <div className="flex items-baseline justify-between font-mono text-xs">
                <span className={over ? "text-red-300" : "text-slate-300"}>
                  {r.key} <span className="text-slate-600">×{r.count}</span>
                  {over && <span className="ml-2 rounded-full border border-red-500/50 px-1.5 text-[10px] uppercase text-red-300" data-testid={`${testId}-over-${r.key}`}>excedido</span>}
                </span>
                <span className={over ? "text-red-300" : "text-slate-100"}>
                  {fmtCredits(r.credits)}{goal != null && <span className="text-slate-500"> / {fmtCredits(goal)}</span>} cr <span className="text-slate-500">· {fmtEur(r.cost_eur)}</span>
                </span>
              </div>
              <div className="relative mt-1 h-1.5 rounded-full bg-surface-subtle">
                <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${(r.credits / max) * 100}%`, background: over ? "#EF4444" : colorFor(r.key, i) }} />
                {goal != null && <div className="absolute inset-y-[-2px] w-px bg-slate-300" style={{ left: `${(goal / max) * 100}%` }} title={`Tope ${fmtCredits(goal)} cr`} />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Breakdowns({ stats, phaseGoals }) {
  return (
    <>
      <Bars title="Por tipo" rows={stats.by_type} colorFor={(k) => TYPE_COLORS[k] || "#64748B"} testId="breakdown-type" />
      <Bars title="Por fase" rows={stats.by_phase} colorFor={(_, i) => PHASE_COLORS[i % PHASE_COLORS.length]} testId="breakdown-phase" goals={phaseGoals} />
      <Bars title="Por origen" rows={stats.by_source} colorFor={(k) => ({ estimado: "#F59E0B", confirmado: "#00FFBF", importado: "#06B6D4" }[k] || "#64748B")} testId="breakdown-source" />
    </>
  );
}

export function Comparison({ comparison }) {
  const { correccion: c, desarrollo: d, correccion_pct } = comparison;
  const Col = ({ label, b, color, testId }) => (
    <div className="flex-1" data-testid={testId}>
      <div className="mono-label" style={{ color }}>{label}</div>
      <div className="mt-1 font-mono text-2xl font-bold">{fmtCredits(b.credits)} <span className="text-sm text-slate-500">cr</span></div>
      <div className="font-mono text-[11px] text-slate-500">{b.count} tareas · {fmtNum(b.minutes / 60, 1)} h · {fmtEur(b.cost_eur)}</div>
    </div>
  );
  return (
    <div className="panel p-4" data-testid="comparison-panel">
      <div className="mono-label mb-3">Corrección vs desarrollo</div>
      <div className="flex gap-4">
        <Col label="Corrección" b={c} color="#F97316" testId="comparison-correccion" />
        <Col label="Desarrollo" b={d} color="#3B82F6" testId="comparison-desarrollo" />
      </div>
      <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-surface-subtle">
        <div className="bg-[#F97316] transition-[width] duration-500" style={{ width: `${correccion_pct}%` }} />
        <div className="bg-[#3B82F6] transition-[width] duration-500" style={{ width: `${100 - correccion_pct}%` }} />
      </div>
      <div className="mt-1.5 font-mono text-[11px] text-slate-400" data-testid="comparison-pct">
        {correccion_pct}% de los créditos van a corregir errores
      </div>
    </div>
  );
}

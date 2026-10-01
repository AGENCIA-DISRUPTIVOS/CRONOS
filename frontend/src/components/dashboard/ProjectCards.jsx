import { fmtCredits } from "@/lib/format";
import { Light } from "@/components/SourceBadge";

const BAR = { green: "bg-emerald-400", amber: "bg-amber-400", red: "bg-red-500", none: "bg-slate-600" };

function Goal({ label, consumed, goal, pct }) {
  if (!goal) return null;
  return (
    <div className="mt-2">
      <div className="flex justify-between font-mono text-[11px] text-slate-400">
        <span>{label}</span>
        <span>{fmtCredits(consumed)} / {fmtCredits(goal)} cr · {pct}%</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-surface-subtle">
        <div className={`h-full rounded-full ${BAR[pct < 70 ? "green" : pct <= 100 ? "amber" : "red"]}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

export function ProjectCards({ projects }) {
  const visible = projects.filter((p) => !p.archived);
  if (visible.length === 0) return null;
  return (
    <div data-testid="project-cards">
      <div className="mono-label mb-3">Proyectos y objetivos</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((p) => (
          <div key={p.id} className="panel p-4" data-testid={`project-card-${p.id}`} style={{ borderLeft: `3px solid ${p.color || "#1E293B"}` }}>
            <div className="flex items-start justify-between gap-2">
              <div className="font-display text-base font-semibold">{p.name}</div>
              <Light status={p.status} testId={`project-light-${p.id}`} />
            </div>
            <div className="mt-1 font-mono text-xs text-slate-500">
              {p.entries} tareas · total <span className="text-slate-200">{fmtCredits(p.consumed_total)} cr</span> · este mes <span className="text-slate-200">{fmtCredits(p.consumed_month)} cr</span>
            </div>
            <Goal label="Objetivo mensual" consumed={p.consumed_month} goal={p.monthly_goal_credits} pct={p.pct_month} />
            <Goal label="Objetivo total" consumed={p.consumed_total} goal={p.goal_credits} pct={p.pct_total} />
            {!p.monthly_goal_credits && !p.goal_credits && <div className="mt-2 font-mono text-[11px] text-slate-600">Sin objetivo definido · configúralo en Ajustes</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

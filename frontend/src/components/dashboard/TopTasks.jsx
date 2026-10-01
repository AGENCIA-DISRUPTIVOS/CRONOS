import { fmtCredits, fmtDate, fmtEur } from "@/lib/format";
import { SourceBadge } from "@/components/SourceBadge";

export function TopTasks({ top, price }) {
  const max = Math.max(...top.map((t) => t.credits), 1);
  return (
    <div className="panel p-4" data-testid="top-tasks">
      <div className="mono-label mb-3">Top tareas por créditos</div>
      {top.length === 0 && <div className="font-mono text-xs text-slate-600">sin datos</div>}
      <ol className="space-y-2">
        {top.map((t, i) => (
          <li key={t.id} className="relative overflow-hidden rounded-md border border-border/60 px-3 py-2" data-testid={`top-task-${i}`}>
            <div className="absolute inset-y-0 left-0 bg-mint/[0.06]" style={{ width: `${(t.credits / max) * 100}%` }} />
            <div className="relative flex items-center gap-3">
              <span className="font-mono text-xs text-slate-600">{String(i + 1).padStart(2, "0")}</span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-slate-100">{t.title}</div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-500">
                  <span>{fmtDate(t.date)}</span><span>·</span><span>{t.project || "—"}</span><span>·</span><span>{t.type}</span><span>·</span><span>{t.phase}</span>
                  <SourceBadge source={t.source} />
                </div>
              </div>
              <div className="text-right font-mono">
                <div className="text-sm font-bold text-mint">{fmtCredits(t.credits)} cr</div>
                <div className="text-[11px] text-slate-500">{fmtEur(t.credits * price)}</div>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

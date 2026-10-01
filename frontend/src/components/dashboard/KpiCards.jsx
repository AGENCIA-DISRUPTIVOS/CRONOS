import { fmtCredits, fmtEur, fmtHours, fmtNum } from "@/lib/format";

export function KpiCards({ stats }) {
  const items = [
    { id: "kpi-total-credits", label: "Créditos", value: fmtCredits(stats.credits), sub: `${fmtNum(stats.avg_credits_per_task, 1)} cr/tarea`, accent: true },
    { id: "kpi-total-cost-eur", label: "Coste", value: fmtEur(stats.cost_eur), sub: `${fmtEur(stats.price_per_credit_eur)} por crédito` },
    { id: "kpi-total-hours", label: "Horas", value: fmtHours(stats.minutes), sub: `${fmtNum(stats.avg_minutes_per_task, 1)} min/tarea` },
    { id: "kpi-total-tasks", label: "Tareas", value: fmtNum(stats.count), sub: `${fmtNum(stats.credits_per_minute, 2)} cr/min` },
    { id: "kpi-total-messages", label: "Mensajes", value: fmtNum(stats.messages), sub: `${fmtNum(stats.credits_per_message, 2)} cr/mensaje` },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {items.map((k, i) => (
        <div key={k.id} data-testid={k.id} className="panel rise p-4" style={{ animationDelay: `${i * 60}ms` }}>
          <div className="mono-label">{k.label}</div>
          <div className={`mt-2 font-mono text-2xl font-bold tracking-tight sm:text-3xl ${k.accent ? "text-mint" : "text-slate-50"}`}>{k.value}</div>
          <div className="mt-1 font-mono text-[11px] text-slate-500">{k.sub}</div>
        </div>
      ))}
    </div>
  );
}

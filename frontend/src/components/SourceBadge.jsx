const STYLES = {
  estimado: "border-amber-700/50 bg-amber-950/60 text-amber-300",
  confirmado: "border-emerald-700/50 bg-emerald-950/70 text-emerald-300",
  importado: "border-cyan-700/50 bg-cyan-950/60 text-cyan-300",
};

export function SourceBadge({ source, testId }) {
  return (
    <span data-testid={testId} className={`inline-block rounded-full border px-2 py-0.5 font-mono text-[11px] ${STYLES[source] || "border-border text-slate-400"}`}>
      {source}
    </span>
  );
}

export function Light({ status, testId }) {
  const c = { green: "bg-emerald-400", amber: "bg-amber-400", red: "bg-red-500", none: "bg-slate-600" }[status] || "bg-slate-600";
  const label = { green: "ok", amber: "atención", red: "excedido", none: "sin objetivo" }[status] || status;
  return (
    <span data-testid={testId} className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase text-slate-400">
      <span className={`h-2 w-2 rounded-full ${c}`} /> {label}
    </span>
  );
}

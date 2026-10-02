import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Markdown } from "@/components/Markdown";

export default function Instrucciones() {
  const { data, isLoading } = useQuery({ queryKey: ["instructions"], queryFn: () => api.get("/cronos/instructions").then((r) => r.data) });
  return (
    <div className="space-y-4" data-testid="instrucciones-page">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="mono-label">Guía</div>
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Instrucciones de uso</h1>
        </div>
        {data?.updated_at && <span className="font-mono text-[11px] text-slate-500">actualizado {data.updated_at.slice(0, 16).replace("T", " ")} · fuente: instrucciones.md</span>}
      </div>
      <div className="panel p-6 sm:p-8">
        {isLoading ? <div className="font-mono text-xs text-slate-500">cargando…</div> : <Markdown testId="instructions-content">{data?.content}</Markdown>}
      </div>
    </div>
  );
}

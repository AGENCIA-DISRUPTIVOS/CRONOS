import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pencil, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Markdown } from "@/components/Markdown";

const SOURCE_STYLE = { manual: "border-border text-slate-400", agente: "border-mint/40 text-mint", ia: "border-purple-500/50 text-purple-300", importado: "border-cyan-700/50 text-cyan-300" };

export function WikiGeneral({ project, q, onOpen, onEdit }) {
  const { user, isAdmin } = useAuth();
  const [active, setActive] = useState(null);
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["wiki-full", project, q],
    queryFn: () => api.get("/cronos/wiki", { params: { full: true, project: project || undefined, q: q || undefined } }).then((r) => r.data),
  });
  const groups = useMemo(() => {
    const byProject = {};
    [...docs].sort((a, b) => (a.created_at || "").localeCompare(b.created_at || "")).forEach((d) => {
      (byProject[d.project || "Sin proyecto"] ||= []).push(d);
    });
    return Object.entries(byProject).sort(([a], [b]) => a.localeCompare(b));
  }, [docs]);

  if (isLoading) return <div className="font-mono text-xs text-slate-500">cargando…</div>;
  if (docs.length === 0) return <div className="panel p-6 font-mono text-xs text-slate-500" data-testid="wiki-general-empty">No hay documentación para esta selección</div>;

  return (
    <div className="grid gap-4 lg:grid-cols-12" data-testid="wiki-general">
      <aside className="lg:col-span-3">
        <div className="panel sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto p-3" data-testid="wiki-toc">
          <div className="mono-label mb-2">Índice · {docs.length} documentos</div>
          {groups.map(([proj, list]) => (
            <div key={proj} className="mb-3">
              <div className="mb-1 font-display text-xs font-semibold text-slate-200">{proj} <span className="font-mono text-[10px] text-slate-500">×{list.length}</span></div>
              <ol className="space-y-0.5 border-l border-border pl-2">
                {list.map((d, i) => (
                  <li key={d.id}>
                    <a href={`#doc-${d.id}`} onClick={() => setActive(d.id)} data-testid={`wiki-toc-${d.id}`}
                      className={`block truncate rounded px-1.5 py-0.5 text-[11px] transition-colors hover:text-mint ${active === d.id ? "bg-mint/10 text-mint" : "text-slate-400"}`} title={d.title}>
                      <span className="mr-1 font-mono text-slate-600">{String(i + 1).padStart(2, "0")}</span>{d.title}
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </aside>
      <div className="space-y-6 lg:col-span-9">
        {groups.map(([proj, list]) => (
          <section key={proj} className="panel p-5 sm:p-7" data-testid={`wiki-project-section-${proj}`}>
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2 border-b border-border pb-3">
              <h2 className="font-display text-xl font-bold tracking-tight text-slate-50">{proj}</h2>
              <span className="font-mono text-[11px] text-slate-500">{list.length} documentos · {list[0]?.created_at?.slice(0, 10)} → {list[list.length - 1]?.created_at?.slice(0, 10)}</span>
            </div>
            {list.map((d, i) => (
              <article key={d.id} id={`doc-${d.id}`} className="scroll-mt-24 border-b border-border/60 py-6 last:border-0" data-testid={`wiki-section-${d.id}`}>
                <div className="mb-3 flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-500">
                  <span className="text-slate-600">{String(i + 1).padStart(2, "0")}</span>
                  <span className={`rounded-full border px-2 py-0.5 ${SOURCE_STYLE[d.source] || SOURCE_STYLE.manual}`}>{d.source}</span>
                  <span>{d.author?.split("@")[0]}</span><span>·</span><span>{d.updated_at?.slice(0, 10)}</span>
                  {d.tags?.map((t) => <span key={t} className="rounded-full bg-surface-subtle px-1.5 py-px text-slate-300">#{t}</span>)}
                  <span className="ml-auto flex gap-1">
                    {(isAdmin || d.author === user.email) && <button className="btn-ghost h-7 w-7" title="Editar" data-testid={`wiki-section-edit-${d.id}`} onClick={() => onEdit(d)}><Pencil size={13} /></button>}
                    <button className="btn-ghost h-7 w-7" title="Abrir ficha" data-testid={`wiki-section-open-${d.id}`} onClick={() => onOpen(d.id)}><ExternalLink size={13} /></button>
                  </span>
                </div>
                <Markdown>{d.content}</Markdown>
              </article>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}

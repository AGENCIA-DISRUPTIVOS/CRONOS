import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pencil, ExternalLink, ChevronDown, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Markdown } from "@/components/Markdown";
import { ProjectOverview } from "@/components/ProjectOverview";

const SOURCE_STYLE = { manual: "border-border text-slate-400", agente: "border-mint/40 text-mint", ia: "border-purple-500/50 text-purple-300", importado: "border-cyan-700/50 text-cyan-300" };

function Iteration({ d, i, open, onToggle, onOpen, onEdit, canEdit }) {
  return (
    <article id={`doc-${d.id}`} className="scroll-mt-24 border-b border-border/60 last:border-0" data-testid={`wiki-section-${d.id}`}>
      <div className="flex flex-wrap items-center gap-2 py-2.5 font-mono text-[11px] text-slate-500">
        <button className="flex min-w-0 flex-1 items-center gap-2 text-left" onClick={onToggle} data-testid={`wiki-iteration-toggle-${d.id}`}>
          {open ? <ChevronDown size={14} className="shrink-0 text-mint" /> : <ChevronRight size={14} className="shrink-0" />}
          <span className="text-slate-600">{String(i + 1).padStart(2, "0")}</span>
          <span className="truncate text-sm text-slate-100">{d.title}</span>
        </button>
        <span className={`rounded-full border px-2 py-0.5 ${SOURCE_STYLE[d.source] || SOURCE_STYLE.manual}`}>{d.source}</span>
        <span>{d.updated_at?.slice(0, 10)}</span>
        {d.tags?.slice(0, 3).map((t) => <span key={t} className="hidden rounded-full bg-surface-subtle px-1.5 py-px text-slate-300 sm:inline">#{t}</span>)}
        <span className="flex gap-1">
          {canEdit && <button className="btn-ghost h-7 w-7" title="Editar" data-testid={`wiki-section-edit-${d.id}`} onClick={() => onEdit(d)}><Pencil size={13} /></button>}
          <button className="btn-ghost h-7 w-7" title="Abrir ficha" data-testid={`wiki-section-open-${d.id}`} onClick={() => onOpen(d.id)}><ExternalLink size={13} /></button>
        </span>
      </div>
      {open && <div className="mb-4 rounded-md border border-border bg-[#0A1019] p-4" data-testid={`wiki-iteration-content-${d.id}`}><Markdown>{d.content}</Markdown></div>}
    </article>
  );
}

export function WikiGeneral({ project, q, onOpen, onEdit }) {
  const { user, isAdmin } = useAuth();
  const [open, setOpen] = useState({});
  const [showIter, setShowIter] = useState({});
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["wiki-full", project, q],
    queryFn: () => api.get("/cronos/wiki", { params: { full: true, project: project || undefined, q: q || undefined } }).then((r) => r.data),
  });
  const groups = useMemo(() => {
    const byProject = {};
    [...docs].sort((a, b) => (a.created_at || "").localeCompare(b.created_at || "")).forEach((d) => { (byProject[d.project || "Sin proyecto"] ||= []).push(d); });
    return Object.entries(byProject).sort(([a], [b]) => a.localeCompare(b));
  }, [docs]);
  const reveal = (proj, id) => { setShowIter((s) => ({ ...s, [proj]: true })); setOpen((o) => ({ ...o, [id]: true })); };

  if (isLoading) return <div className="font-mono text-xs text-slate-500">cargando…</div>;
  if (docs.length === 0) return <div className="panel p-6 font-mono text-xs text-slate-500" data-testid="wiki-general-empty">No hay documentación para esta selección</div>;

  return (
    <div className="grid gap-4 lg:grid-cols-12" data-testid="wiki-general">
      <aside className="min-w-0 lg:col-span-3">
        <div className="panel sticky top-20 max-h-[calc(100vh-6rem)] overflow-x-hidden overflow-y-auto p-3" data-testid="wiki-toc">
          <div className="mono-label mb-2">Índice</div>
          {groups.map(([proj, list]) => (
            <div key={proj} className="mb-3">
              <a href={`#project-${proj}`} className="mb-1 block font-display text-xs font-semibold text-slate-200 hover:text-mint" data-testid={`wiki-toc-project-${proj}`}>{proj}</a>
              <ol className="space-y-0.5 border-l border-border pl-2">
                <li><a href={`#project-${proj}`} className="block rounded px-1.5 py-0.5 text-[11px] text-mint/80 hover:text-mint">Documento global</a></li>
                {list.map((d, i) => (
                  <li key={d.id}>
                    <a href={`#doc-${d.id}`} onClick={() => reveal(proj, d.id)} data-testid={`wiki-toc-${d.id}`} className="block max-w-full truncate rounded px-1.5 py-0.5 text-[11px] text-slate-400 transition-colors hover:text-mint" title={d.title}>
                      <span className="mr-1 font-mono text-slate-600">{String(i + 1).padStart(2, "0")}</span>{d.title}
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </aside>
      <div className="min-w-0 space-y-6 lg:col-span-9">
        {groups.map(([proj, list]) => (
          <section key={proj} id={`project-${proj}`} className="panel scroll-mt-24 p-5 sm:p-7" data-testid={`wiki-project-section-${proj}`}>
            <h2 className="mb-4 border-b border-border pb-3 font-display text-2xl font-bold tracking-tight text-slate-50">{proj}</h2>
            <ProjectOverview project={proj} />
            <div className="mt-6 border-t border-border pt-4">
              <button data-testid={`wiki-iterations-toggle-${proj}`} className="btn-secondary h-8 text-xs" onClick={() => setShowIter((s) => ({ ...s, [proj]: !s[proj] }))}>
                {showIter[proj] ? <ChevronDown size={13} /> : <ChevronRight size={13} />} {showIter[proj] ? "Ocultar" : "Ver"} iteraciones y fichas ({list.length})
              </button>
              {showIter[proj] && (
                <div className="mt-3" data-testid={`wiki-iterations-${proj}`}>
                  {list.map((d, i) => (
                    <Iteration key={d.id} d={d} i={i} open={Boolean(open[d.id])} onToggle={() => setOpen((o) => ({ ...o, [d.id]: !o[d.id] }))} onOpen={onOpen} onEdit={onEdit} canEdit={isAdmin || d.author === user.email} />
                  ))}
                </div>
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

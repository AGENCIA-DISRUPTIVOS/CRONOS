import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Bot, Eye, Pencil, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Markdown } from "@/components/Markdown";

const SOURCE_STYLE = { manual: "border-border text-slate-400", agente: "border-mint/40 text-mint", ia: "border-purple-500/50 text-purple-300", importado: "border-cyan-700/50 text-cyan-300" };
const EMPTY = { title: "", content: "", tags: "", project: "", entry_id: null, source: "manual" };

function WikiEditor({ initial, meta, onCancel, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [preview, setPreview] = useState(false);
  const [ai, setAi] = useState({ open: false, entry_id: "", description: "", busy: false });
  const { data: entries = [] } = useQuery({ queryKey: ["entries", {}], queryFn: () => api.get("/cronos/entries").then((r) => r.data), enabled: ai.open });
  useEffect(() => { setForm({ ...EMPTY, ...initial, tags: (initial?.tags || []).join(", ") }); }, [initial]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const generate = async () => {
    setAi((a) => ({ ...a, busy: true }));
    try {
      const { data } = await api.post("/cronos/wiki/generate", { entry_id: ai.entry_id || null, description: ai.description, title: form.title });
      setForm((f) => ({ ...f, title: f.title || data.title, content: data.content, tags: [...new Set([...(f.tags ? f.tags.split(",").map((t) => t.trim()) : []), ...data.tags])].join(", "), project: f.project || data.project, entry_id: data.entry_id, source: "ia" }));
      setAi((a) => ({ ...a, open: false }));
      toast.success(`Borrador generado con ${data.model_used}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAi((a) => ({ ...a, busy: false }));
    }
  };

  const save = async (e) => {
    e.preventDefault();
    const body = { title: form.title, content: form.content, project: form.project, entry_id: form.entry_id, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) };
    try {
      if (initial?.id) await api.patch(`/cronos/wiki/${initial.id}`, body);
      else await api.post("/cronos/wiki", { ...body, source: form.source });
      toast.success("Documento guardado");
      onSaved();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  return (
    <form onSubmit={save} className="panel space-y-3 p-4" data-testid="wiki-editor">
      <div className="flex flex-wrap items-center gap-2">
        <input data-testid="wiki-title-input" className="field flex-1 font-display text-base font-semibold" placeholder="Título del documento" required value={form.title} onChange={(e) => set("title", e.target.value)} />
        <button type="button" data-testid="wiki-ai-button" className="btn-secondary border-purple-500/40 text-purple-300 hover:text-purple-200" onClick={() => setAi((a) => ({ ...a, open: !a.open }))}><Sparkles size={14} /> Documentar con IA</button>
      </div>
      {ai.open && (
        <div className="rounded-md border border-purple-500/30 bg-purple-500/5 p-3" data-testid="wiki-ai-panel">
          <div className="mono-label mb-2 text-purple-300">Generar borrador (consume créditos de la clave universal)</div>
          <div className="grid gap-2 sm:grid-cols-2">
            <select data-testid="wiki-ai-entry-select" className="field font-mono text-xs" value={ai.entry_id} onChange={(e) => setAi((a) => ({ ...a, entry_id: e.target.value }))}>
              <option value="">— elige una tarea del registro (opcional) —</option>
              {entries.map((en) => <option key={en.id} value={en.id}>{en.date} · {en.title.slice(0, 70)}</option>)}
            </select>
            <input data-testid="wiki-ai-description-input" className="field" placeholder="o describe lo que se ha hecho" value={ai.description} onChange={(e) => setAi((a) => ({ ...a, description: e.target.value }))} />
          </div>
          <button type="button" data-testid="wiki-ai-generate-button" className="btn-primary mt-2 bg-purple-400 hover:bg-purple-300" disabled={ai.busy || (!ai.entry_id && !ai.description.trim())} onClick={generate}>
            <Bot size={14} /> {ai.busy ? "Generando…" : "Generar borrador"}
          </button>
        </div>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        <input data-testid="wiki-tags-input" className="field font-mono text-xs" placeholder="etiquetas separadas por comas" value={form.tags} onChange={(e) => set("tags", e.target.value)} />
        <input data-testid="wiki-project-input" className="field text-xs" list="wiki-projects" placeholder="proyecto" value={form.project || ""} onChange={(e) => set("project", e.target.value)} />
        <datalist id="wiki-projects">{(meta?.projects || []).map((p) => <option key={p} value={p} />)}</datalist>
      </div>
      <div className="flex items-center gap-1 border-b border-border">
        {[["editar", false, Pencil], ["vista previa", true, Eye]].map(([l, v, Icon]) => (
          <button key={l} type="button" data-testid={`wiki-tab-${v ? "preview" : "edit"}`} onClick={() => setPreview(v)} className={`flex items-center gap-1.5 border-b-2 px-3 py-1.5 font-mono text-xs ${preview === v ? "border-mint text-mint" : "border-transparent text-slate-500"}`}><Icon size={12} /> {l}</button>
        ))}
      </div>
      {preview ? (
        <div className="min-h-[320px] rounded-md border border-border bg-[#0A1019] p-4"><Markdown testId="wiki-preview">{form.content || "_Nada que previsualizar_"}</Markdown></div>
      ) : (
        <textarea data-testid="wiki-content-textarea" className="field min-h-[320px] resize-y py-2 font-mono text-xs leading-relaxed" placeholder="Escribe en Markdown…" value={form.content} onChange={(e) => set("content", e.target.value)} />
      )}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel} data-testid="wiki-cancel-button">Cancelar</button>
        <button type="submit" className="btn-primary" data-testid="wiki-save-button">Guardar</button>
      </div>
    </form>
  );
}

function WikiDoc({ id, onBack, onEdit, onDeleted }) {
  const { user, isAdmin } = useAuth();
  const { data: doc } = useQuery({ queryKey: ["wiki", id], queryFn: () => api.get(`/cronos/wiki/${id}`).then((r) => r.data) });
  if (!doc) return <div className="font-mono text-xs text-slate-500">cargando…</div>;
  const canEdit = isAdmin || doc.author === user.email;
  const remove = async () => {
    if (!window.confirm(`¿Borrar «${doc.title}»?`)) return;
    try { await api.delete(`/cronos/wiki/${id}`); toast.success("Documento borrado"); onDeleted(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="panel p-6" data-testid="wiki-doc">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <button className="btn-secondary" onClick={onBack} data-testid="wiki-back-button"><ArrowLeft size={14} /> Volver</button>
        {canEdit && (
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => onEdit(doc)} data-testid="wiki-edit-button"><Pencil size={14} /> Editar</button>
            <button className="btn-secondary hover:text-red-400" onClick={remove} data-testid="wiki-delete-button"><Trash2 size={14} /></button>
          </div>
        )}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-500">
        <span className={`rounded-full border px-2 py-0.5 ${SOURCE_STYLE[doc.source] || SOURCE_STYLE.manual}`}>{doc.source}</span>
        <span>{doc.author}</span><span>·</span><span>{doc.updated_at?.slice(0, 16).replace("T", " ")}</span>
        {doc.project && <><span>·</span><span className="text-slate-300">{doc.project}</span></>}
        {doc.tags?.map((t) => <span key={t} className="rounded-full bg-surface-subtle px-2 py-0.5 text-slate-300">#{t}</span>)}
        {doc.history?.length > 0 && <span className="text-slate-600">· {doc.history.length} revisiones</span>}
      </div>
      <Markdown testId="wiki-doc-content">{doc.content}</Markdown>
    </div>
  );
}

export default function Wiki() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [mode, setMode] = useState({ view: "list", id: null, initial: null });
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");
  const [project, setProject] = useState(searchParams.get("project") || "");
  const entryParam = searchParams.get("entry");
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: () => api.get("/cronos/meta").then((r) => r.data) });
  const { data: docs = [], isLoading } = useQuery({ queryKey: ["wiki-list", q, tag, project], queryFn: () => api.get("/cronos/wiki", { params: { q: q || undefined, tag: tag || undefined, project: project || undefined } }).then((r) => r.data) });
  const { data: tags = [] } = useQuery({ queryKey: ["wiki-tags"], queryFn: () => api.get("/cronos/wiki/tags").then((r) => r.data) });
  useEffect(() => {
    if (!entryParam) return;
    api.get("/cronos/wiki", { params: { entry_id: entryParam } }).then(({ data }) => {
      if (data[0]) setMode({ view: "doc", id: data[0].id, initial: null });
      else toast.warning("Esta tarea todavía no tiene documento en la wiki");
      setSearchParams({}, { replace: true });
    });
  }, [entryParam, setSearchParams]);
  const back = () => { qc.invalidateQueries({ queryKey: ["wiki-list"] }); qc.invalidateQueries({ queryKey: ["wiki-tags"] }); qc.invalidateQueries({ queryKey: ["wiki"] }); setMode({ view: "list", id: null, initial: null }); };

  return (
    <div className="space-y-4" data-testid="wiki-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mono-label">Wiki</div>
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Documentación de iteraciones</h1>
        </div>
        {mode.view === "list" && <button data-testid="wiki-new-button" className="btn-primary" onClick={() => setMode({ view: "edit", id: null, initial: {} })}><Plus size={14} /> Nuevo documento</button>}
      </div>
      {mode.view === "edit" && <WikiEditor initial={mode.initial} meta={meta} onCancel={back} onSaved={back} />}
      {mode.view === "doc" && <WikiDoc id={mode.id} onBack={back} onEdit={(doc) => setMode({ view: "edit", id: doc.id, initial: doc })} onDeleted={back} />}
      {mode.view === "list" && (
        <>
          <div className="panel flex flex-wrap items-center gap-2 p-3">
            <div className="relative flex-1"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" /><input data-testid="wiki-search-input" className="field pl-9" placeholder="Buscar en títulos, contenido y etiquetas…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
            <select data-testid="wiki-project-select" className="field w-auto font-mono text-xs" value={project} onChange={(e) => setProject(e.target.value)}>
              <option value="">todos los proyectos</option>
              {(meta?.projects || []).map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <select data-testid="wiki-tag-select" className="field w-auto font-mono text-xs" value={tag} onChange={(e) => setTag(e.target.value)}>
              <option value="">todas las etiquetas</option>
              {tags.map((t) => <option key={t} value={t}>#{t}</option>)}
            </select>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="wiki-list">
            {isLoading && <div className="font-mono text-xs text-slate-500">cargando…</div>}
            {!isLoading && docs.length === 0 && <div className="font-mono text-xs text-slate-500" data-testid="wiki-empty">Todavía no hay documentos</div>}
            {docs.map((d) => (
              <button key={d.id} data-testid={`wiki-card-${d.id}`} onClick={() => setMode({ view: "doc", id: d.id, initial: null })} className="panel rise flex flex-col gap-2 p-4 text-left hover:border-mint/50">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-display text-base font-semibold leading-tight text-slate-100">{d.title}</div>
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] ${SOURCE_STYLE[d.source] || SOURCE_STYLE.manual}`}>{d.source}</span>
                </div>
                <p className="line-clamp-3 text-xs leading-relaxed text-slate-400">{d.excerpt?.replace(/[#*_`>]/g, "")}</p>
                <div className="mt-auto flex flex-wrap items-center gap-1.5 font-mono text-[10px] text-slate-500">
                  <span>{d.author?.split("@")[0]}</span><span>·</span><span>{d.updated_at?.slice(0, 10)}</span>
                  {d.project && <><span>·</span><span className="text-slate-400">{d.project}</span></>}
                  {d.tags?.slice(0, 4).map((t) => <span key={t} className="rounded-full bg-surface-subtle px-1.5 py-px text-slate-300">#{t}</span>)}
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

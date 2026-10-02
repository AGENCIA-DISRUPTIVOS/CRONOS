import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Eye, Pencil, Save, Sparkles, X } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmtCredits, fmtEur, fmtHours, fmtDate } from "@/lib/format";
import { Markdown } from "@/components/Markdown";

export function ProjectOverview({ project }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["wiki-overview", project], queryFn: () => api.get("/cronos/wiki-overview", { params: { project } }).then((r) => r.data) });
  const [editing, setEditing] = useState(false);
  const [preview, setPreview] = useState(false);
  const [draft, setDraft] = useState({ content: "", status: "borrador" });
  const [busy, setBusy] = useState(false);
  const ov = data?.overview;
  const st = data?.stats;
  useEffect(() => { if (ov) setDraft({ content: ov.content || "", status: ov.status || "borrador" }); }, [ov]);

  const save = async () => {
    try {
      await api.put("/cronos/wiki-overview", { project, ...draft });
      toast.success("Documento global guardado");
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["wiki-overview", project] });
    } catch (e) { toast.error(errMsg(e)); }
  };
  const regenerate = async () => {
    if (!window.confirm("Se generará un nuevo borrador con IA a partir de todas las fichas del proyecto (consume créditos). ¿Continuar?")) return;
    setBusy(true);
    try {
      const { data: g } = await api.post("/cronos/wiki-overview/generate", { project });
      setDraft({ content: g.content, status: "borrador" });
      setEditing(true);
      setPreview(true);
      toast.success(`Borrador generado con ${g.model_used} a partir de ${g.docs_used} fichas · revísalo y guarda`);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div data-testid={`overview-${project}`}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="mono-label">Documento global</span>
        {ov && <span data-testid="overview-status" className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase ${ov.status === "revisado" ? "border-mint/40 text-mint" : "border-amber-500/50 text-amber-300"}`}>{ov.status === "revisado" ? "revisado" : "borrador pendiente de revisión"}</span>}
        {ov && <span className="font-mono text-[11px] text-slate-500">{ov.updated_by?.split("@")[0]} · {ov.updated_at?.slice(0, 16).replace("T", " ")}</span>}
        <span className="ml-auto flex gap-1.5">
          <button data-testid="overview-regenerate-button" className="btn-secondary h-8 border-purple-500/40 text-xs text-purple-300" onClick={regenerate} disabled={busy}><Sparkles size={13} /> {busy ? "Generando…" : "Regenerar con IA"}</button>
          {!editing && <button data-testid="overview-edit-button" className="btn-secondary h-8 text-xs" onClick={() => setEditing(true)}><Pencil size={13} /> Editar</button>}
        </span>
      </div>
      {st && (
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6" data-testid="overview-stats">
          {[["Tareas", st.count], ["Horas", fmtHours(st.minutes)], ["Créditos", fmtCredits(st.credits)], ["Coste", fmtEur(st.cost_eur)], ["Mensajes", st.messages], ["Periodo", st.first_date ? `${fmtDate(st.first_date).slice(0, 5)} → ${fmtDate(st.last_date).slice(0, 5)}` : "—"]].map(([l, v]) => (
            <div key={l} className="rounded-md border border-border bg-[#0A1019] px-3 py-2"><div className="mono-label text-[10px]">{l}</div><div className="font-mono text-base font-bold text-mint">{v}</div></div>
          ))}
        </div>
      )}
      {editing ? (
        <div className="space-y-2" data-testid="overview-editor">
          <div className="flex items-center gap-2">
            <button type="button" data-testid="overview-tab-edit" onClick={() => setPreview(false)} className={`flex items-center gap-1 border-b-2 px-2 py-1 font-mono text-xs ${!preview ? "border-mint text-mint" : "border-transparent text-slate-500"}`}><Pencil size={12} /> editar</button>
            <button type="button" data-testid="overview-tab-preview" onClick={() => setPreview(true)} className={`flex items-center gap-1 border-b-2 px-2 py-1 font-mono text-xs ${preview ? "border-mint text-mint" : "border-transparent text-slate-500"}`}><Eye size={12} /> vista previa</button>
            <select data-testid="overview-status-select" className="field ml-auto h-8 w-auto font-mono text-xs" value={draft.status} onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value }))}>
              <option value="borrador">borrador pendiente de revisión</option>
              <option value="revisado">revisado</option>
            </select>
          </div>
          {preview ? <div className="rounded-md border border-border bg-[#0A1019] p-4"><Markdown>{draft.content}</Markdown></div>
            : <textarea data-testid="overview-textarea" className="field min-h-[420px] resize-y py-2 font-mono text-xs leading-relaxed" value={draft.content} onChange={(e) => setDraft((d) => ({ ...d, content: e.target.value }))} />}
          <div className="flex justify-end gap-2">
            <button className="btn-secondary h-8 text-xs" onClick={() => { setEditing(false); setDraft({ content: ov?.content || "", status: ov?.status || "borrador" }); }} data-testid="overview-cancel-button"><X size={13} /> Cancelar</button>
            <button className="btn-primary h-8 text-xs" onClick={save} data-testid="overview-save-button"><Save size={13} /> Guardar</button>
          </div>
        </div>
      ) : ov ? (
        <Markdown testId="overview-content">{ov.content}</Markdown>
      ) : (
        <div className="rounded-md border border-dashed border-border p-4 font-mono text-xs text-slate-500" data-testid="overview-empty">Este proyecto aún no tiene documento global. Pulsa «Editar» para escribirlo o «Regenerar con IA» para generar un borrador.</div>
      )}
    </div>
  );
}

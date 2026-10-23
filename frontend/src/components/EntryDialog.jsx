import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { todayIso } from "@/lib/format";

const BLANK = { title: "", project: "", type: "desarrollo", phase: "otra", date: todayIso(), minutes: 0, messages: 0, credits: 0, source: "estimado", notes: "", user: "", model: "", tokens_in: 0, tokens_out: 0, cost_eur: 0, tokens_estimated: true, app: "", summary: "" };

export function EntryDialog({ open, onOpenChange, initial, meta, onSaved }) {
  const { user: me, isAdmin } = useAuth();
  const [form, setForm] = useState(BLANK);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm({ ...BLANK, user: me?.email || "", ...(initial || {}) });
  }, [open, initial, me]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const isEdit = Boolean(initial?.id);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    const body = { ...form, minutes: Number(form.minutes), messages: Number(form.messages), credits: Number(form.credits),
      tokens_in: Number(form.tokens_in) || 0, tokens_out: Number(form.tokens_out) || 0, cost_eur: Number(form.cost_eur) || 0 };
    delete body.id; delete body.created_at; delete body.updated_at; delete body.created_by; delete body.external_id; delete body.channel;
    if (!body.user) delete body.user;
    try {
      if (isEdit) await api.patch(`/cronos/entries/${initial.id}`, body);
      else await api.post("/cronos/entries", body);
      toast.success(isEdit ? "Entrada actualizada" : "Entrada guardada");
      onSaved?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, children }) => (
    <label className="flex flex-col gap-1">
      <span className="mono-label">{label}</span>
      {children}
    </label>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-border bg-surface" data-testid="entry-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">{isEdit ? "Editar entrada" : "Nueva entrada"}</DialogTitle>
          <DialogDescription className="text-slate-500">Revisa los datos antes de guardar.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-4">
            <Field label="Título">
              <input data-testid="entry-title-input" className="field" required value={form.title} onChange={(e) => set("title", e.target.value)} />
            </Field>
          </div>
          <div className="col-span-2">
            <Field label="Proyecto">
              <input data-testid="entry-project-input" className="field" list="projects-list" value={form.project} onChange={(e) => set("project", e.target.value)} />
              <datalist id="projects-list">{(meta?.projects || []).map((p) => <option key={p} value={p} />)}</datalist>
            </Field>
          </div>
          <Field label="Usuario">
            <select data-testid="entry-user-select" className="field font-mono text-xs" value={form.user || ""} disabled={!isAdmin} onChange={(e) => set("user", e.target.value)}>
              {[...new Set([me?.email, form.user, ...(meta?.users || [])].filter(Boolean))].map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </Field>
          <Field label="Modelo IA">
            <select data-testid="entry-model-select" className="field font-mono text-xs" value={form.model || ""} onChange={(e) => set("model", e.target.value)}>
              <option value="">— sin indicar —</option>
              {[...new Set([form.model, ...(meta?.models || [])].filter(Boolean))].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="Tipo">
            <select data-testid="entry-type-select" className="field font-mono" value={form.type} onChange={(e) => set("type", e.target.value)}>
              {(meta?.types || []).map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Fase">
            <select data-testid="entry-phase-select" className="field font-mono" value={form.phase} onChange={(e) => set("phase", e.target.value)}>
              {(meta?.phases || []).map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Fecha">
            <input data-testid="entry-date-input" type="date" required className="field font-mono" value={form.date} onChange={(e) => set("date", e.target.value)} />
          </Field>
          <Field label="Minutos">
            <input data-testid="entry-minutes-input" type="number" min="0" className="field font-mono" value={form.minutes} onChange={(e) => set("minutes", e.target.value)} />
          </Field>
          <Field label="Mensajes">
            <input data-testid="entry-messages-input" type="number" min="0" className="field font-mono" value={form.messages} onChange={(e) => set("messages", e.target.value)} />
          </Field>
          <Field label="Créditos">
            <input data-testid="entry-credits-input" type="number" min="0" step="0.01" className="field font-mono" value={form.credits} onChange={(e) => set("credits", e.target.value)} />
          </Field>
          <Field label="Origen">
            <select data-testid="entry-source-select" className="field font-mono" value={form.source} onChange={(e) => set("source", e.target.value)}>
              {(meta?.sources || []).map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Tokens entrada">
            <input data-testid="entry-tokens-in-input" type="number" min="0" className="field font-mono" value={form.tokens_in} onChange={(e) => set("tokens_in", e.target.value)} />
          </Field>
          <Field label="Tokens salida">
            <input data-testid="entry-tokens-out-input" type="number" min="0" className="field font-mono" value={form.tokens_out} onChange={(e) => set("tokens_out", e.target.value)} />
          </Field>
          <Field label="Coste real (€)">
            <input data-testid="entry-cost-eur-input" type="number" min="0" step="0.0001" className="field font-mono" value={form.cost_eur} onChange={(e) => set("cost_eur", e.target.value)} />
          </Field>
          <Field label="App">
            <input data-testid="entry-app-input" className="field" value={form.app || ""} onChange={(e) => set("app", e.target.value)} />
          </Field>
          <label className="col-span-2 flex items-center gap-2 sm:col-span-4">
            <input data-testid="entry-tokens-estimated-input" type="checkbox" checked={form.tokens_estimated !== false} onChange={(e) => set("tokens_estimated", e.target.checked)} />
            <span className="text-xs text-slate-400">Tokens estimados (desmarca si son los exactos de la plataforma)</span>
          </label>
          <div className="col-span-2 sm:col-span-4">
            <Field label="Resumen de lo implementado (alimenta la wiki)">
              <textarea data-testid="entry-summary-input" className="field h-24 resize-y py-2 text-sm" value={form.summary || ""} onChange={(e) => set("summary", e.target.value)} />
            </Field>
          </div>
          <div className="col-span-2 sm:col-span-4">
            <Field label="Notas">
              <input data-testid="entry-notes-input" className="field" value={form.notes || ""} onChange={(e) => set("notes", e.target.value)} />
            </Field>
          </div>
          <div className="col-span-2 flex justify-end gap-2 pt-2 sm:col-span-4">
            <button type="button" className="btn-secondary" onClick={() => onOpenChange(false)} data-testid="entry-cancel-button">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={saving} data-testid="entry-save-button">
              {saving ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

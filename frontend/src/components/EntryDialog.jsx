import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errMsg } from "@/lib/api";
import { todayIso } from "@/lib/format";

const BLANK = { title: "", project: "", type: "desarrollo", phase: "otra", date: todayIso(), minutes: 0, messages: 0, credits: 0, source: "estimado", notes: "" };

export function EntryDialog({ open, onOpenChange, initial, meta, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm({ ...BLANK, ...(initial || {}) });
  }, [open, initial]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const isEdit = Boolean(initial?.id);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    const body = { ...form, minutes: Number(form.minutes), messages: Number(form.messages), credits: Number(form.credits) };
    delete body.id; delete body.created_at; delete body.updated_at; delete body.created_by;
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
          <div className="col-span-2 sm:col-span-3">
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

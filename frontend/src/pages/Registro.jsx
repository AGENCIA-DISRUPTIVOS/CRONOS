import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BookOpen, Download, Pencil, Plus, Trash2, Wand2 } from "lucide-react";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { api, cleanParams, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmtCredits, fmtDate, fmtEur } from "@/lib/format";
import { EMPTY_FILTERS, FiltersBar } from "@/components/FiltersBar";
import { SourceBadge } from "@/components/SourceBadge";
import { EntryDialog } from "@/components/EntryDialog";

function QuickAdd({ meta, onDraft }) {
  const [line, setLine] = useState("");
  const [busy, setBusy] = useState(false);
  const parse = async () => {
    if (!line.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/cronos/parse-line", { line });
      data.warnings?.forEach((w) => toast.warning(w));
      onDraft(data.draft);
      setLine("");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="panel border-mint/20 p-3" data-testid="quick-add-panel">
      <div className="mono-label mb-2">Alta rápida · pega la línea del agente</div>
      <div className="flex gap-2">
        <input
          data-testid="quick-add-cronos-input"
          className="field font-mono"
          placeholder={meta?.line_format || "#cronos | título | tipo | fase | minutos | mensajes | créditos [| proyecto]"}
          value={line}
          onChange={(e) => setLine(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && parse()}
        />
        <button data-testid="quick-add-submit-button" className="btn-primary shrink-0" onClick={parse} disabled={busy}>
          <Wand2 size={14} /> Analizar
        </button>
      </div>
    </div>
  );
}

export default function Registro() {
  const { isAdmin, user: me } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, user: searchParams.get("user") || "" });
  const canEdit = (e) => isAdmin || e.user === me?.email || e.created_by === me?.email;
  const [dialog, setDialog] = useState({ open: false, initial: null });
  const [toDelete, setToDelete] = useState(null);
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: () => api.get("/cronos/meta").then((r) => r.data) });
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get("/cronos/settings").then((r) => r.data) });
  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["entries", filters],
    queryFn: () => api.get("/cronos/entries", { params: cleanParams(filters) }).then((r) => r.data),
  });
  const price = settings?.price_per_credit_eur ?? 0;
  const invalidate = () => qc.invalidateQueries();

  const remove = async () => {
    try {
      await api.delete(`/cronos/entries/${toDelete.id}`);
      toast.success("Entrada eliminada");
      invalidate();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setToDelete(null);
    }
  };

  const exportCsv = async () => {
    const res = await api.get("/cronos/export.csv", { params: cleanParams(filters), responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = Object.assign(document.createElement("a"), { href: url, download: "cronos.csv" });
    a.click();
    URL.revokeObjectURL(url);
  };

  const totals = entries.reduce((a, e) => ({ credits: a.credits + e.credits, minutes: a.minutes + e.minutes, messages: a.messages + e.messages }), { credits: 0, minutes: 0, messages: 0 });

  return (
    <div className="space-y-4" data-testid="registro-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mono-label">Registro</div>
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Tareas registradas</h1>
        </div>
        <div className="flex gap-2">
          <button data-testid="export-csv-button" className="btn-secondary" onClick={exportCsv}><Download size={14} /> CSV</button>
          <button data-testid="new-entry-button" className="btn-primary" onClick={() => setDialog({ open: true, initial: null })}><Plus size={14} /> Nueva</button>
        </div>
      </div>
      <QuickAdd meta={meta} onDraft={(draft) => setDialog({ open: true, initial: draft })} />
      <FiltersBar filters={filters} setFilters={setFilters} meta={meta} />

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[1180px] border-collapse" data-testid="records-table">
          <thead>
            <tr>
              <th className="th">Fecha</th><th className="th">Título</th><th className="th">Proyecto</th><th className="th">Usuario</th><th className="th">Modelo</th><th className="th">Tipo</th><th className="th">Fase</th>
              <th className="th text-right">Min</th><th className="th text-right">Msg</th><th className="th text-right">Créditos</th><th className="th text-right">€</th><th className="th">Origen</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="td font-mono text-xs text-slate-500" colSpan={13}>cargando…</td></tr>}
            {!isLoading && entries.length === 0 && <tr><td className="td font-mono text-xs text-slate-500" colSpan={13} data-testid="records-empty">Sin entradas para estos filtros</td></tr>}
            {entries.map((e) => (
              <tr key={e.id} className="group transition-colors hover:bg-surface-subtle/60" data-testid={`record-row-${e.id}`}>
                <td className="td whitespace-nowrap font-mono text-xs text-slate-400">{fmtDate(e.date)}</td>
                <td className="td max-w-[380px]">
                  <div className="truncate text-slate-100" title={e.title}>{e.title}</div>
                  {e.notes && <div className="truncate text-[11px] text-slate-500" title={e.notes}>{e.notes}</div>}
                </td>
                <td className="td text-xs text-slate-300">{e.project || "—"}</td>
                <td className="td font-mono text-[11px] text-slate-400" title={e.user}>{(e.user || "—").split("@")[0]}</td>
                <td className="td font-mono text-[11px] text-slate-300">{e.model || "—"}</td>
                <td className="td font-mono text-xs">{e.type}</td>
                <td className="td font-mono text-xs">{e.phase}</td>
                <td className="td text-right font-mono text-xs">{e.minutes}</td>
                <td className="td text-right font-mono text-xs">{e.messages}</td>
                <td className="td text-right font-mono text-sm font-semibold text-mint">
                  {fmtCredits(e.credits)}
                  {e.estimated_credits != null && e.source === "confirmado" && <div className="text-[10px] font-normal text-slate-500">est. {fmtCredits(e.estimated_credits)}</div>}
                </td>
                <td className="td text-right font-mono text-xs text-slate-300">{fmtEur(e.credits * price)}</td>
                <td className="td"><SourceBadge source={e.source} testId={`record-source-${e.id}`} /></td>
                <td className="td">
                  <div className="flex justify-end gap-1 opacity-60 transition-opacity group-hover:opacity-100">
                    <button data-testid={`wiki-entry-${e.id}`} className="btn-ghost" onClick={() => navigate(`/wiki?entry=${e.id}`)} title="Ver en la wiki"><BookOpen size={14} /></button>
                    {canEdit(e) && (
                      <>
                        <button data-testid={`edit-entry-${e.id}`} className="btn-ghost" onClick={() => setDialog({ open: true, initial: e })} title="Editar"><Pencil size={14} /></button>
                        <button data-testid={`delete-entry-${e.id}`} className="btn-ghost hover:text-red-400" onClick={() => setToDelete(e)} title="Borrar"><Trash2 size={14} /></button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          {entries.length > 0 && (
            <tfoot>
              <tr className="bg-[#0A1019]" data-testid="records-totals">
                <td className="td font-mono text-xs text-slate-400" colSpan={7}>{entries.length} entradas</td>
                <td className="td text-right font-mono text-xs">{totals.minutes}</td>
                <td className="td text-right font-mono text-xs">{totals.messages}</td>
                <td className="td text-right font-mono text-sm font-bold text-mint">{fmtCredits(totals.credits)}</td>
                <td className="td text-right font-mono text-xs">{fmtEur(totals.credits * price)}</td>
                <td className="td" colSpan={2} />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <EntryDialog open={dialog.open} onOpenChange={(o) => setDialog((d) => ({ ...d, open: o }))} initial={dialog.initial} meta={meta} onSaved={invalidate} />

      <AlertDialog open={Boolean(toDelete)} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent className="border-border bg-surface" data-testid="delete-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">¿Borrar esta entrada?</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">«{toDelete?.title}» se eliminará de forma permanente.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="btn-secondary" data-testid="delete-cancel-button">Cancelar</AlertDialogCancel>
            <AlertDialogAction className="bg-red-500 text-white hover:bg-red-600" onClick={remove} data-testid="delete-confirm-button">Borrar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

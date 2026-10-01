import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCheck, History, Search, Upload } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmtCredits, fmtDate } from "@/lib/format";

const EXAMPLE = `2026-10-01 09:12  Agente Emergent · Central Disruptivos   640,5 créditos
01/10/2026 18:40  Agente Emergent · Cronos                  52 cr
2026-09-30        Agente Emergent                           195.3`;

function StatementsHistory() {
  const { data: statements = [] } = useQuery({ queryKey: ["statements"], queryFn: () => api.get("/cronos/statements").then((r) => r.data) });
  const total = statements.reduce((a, s) => a + s.credits, 0);
  return (
    <div className="panel overflow-x-auto" data-testid="statements-history">
      <div className="flex items-center justify-between p-4 pb-2">
        <div className="mono-label flex items-center gap-1.5"><History size={12} /> Historial de cuadres</div>
        <div className="font-mono text-xs text-slate-500">{statements.length} días · {fmtCredits(total)} cr reales</div>
      </div>
      {statements.length === 0 ? (
        <div className="px-4 pb-4 font-mono text-xs text-slate-600" data-testid="statements-empty">Todavía no se ha cuadrado ningún día</div>
      ) : (
        <table className="w-full min-w-[560px]">
          <thead><tr><th className="th">Día</th><th className="th text-right">Créditos reales</th><th className="th">Cuadrado por</th><th className="th">Fecha de cuadre</th></tr></thead>
          <tbody>
            {statements.map((s) => (
              <tr key={s.date} className="hover:bg-surface-subtle/60" data-testid={`statement-row-${s.date}`}>
                <td className="td font-mono text-sm">{fmtDate(s.date)}</td>
                <td className="td text-right font-mono text-sm font-semibold text-mint">{fmtCredits(s.credits)}</td>
                <td className="td font-mono text-xs text-slate-300">{s.by}</td>
                <td className="td font-mono text-xs text-slate-500">{s.imported_at?.slice(0, 16).replace("T", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function Cuadrar() {
  const { isAdmin } = useAuth();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileRef = useRef(null);

  const runPreview = async (source = text) => {
    setBusy(true);
    setResult(null);
    try {
      const { data } = await api.post("/cronos/reconcile/preview", { text: source });
      setPreview(data);
      setSelected(Object.fromEntries(data.days.map((d) => [d.date, true])));
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const onFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const content = String(reader.result || "");
      setText(content);
      setFileName(file.name);
      toast.success(`${file.name} cargado`);
      runPreview(content);
    };
    reader.onerror = () => toast.error("No se pudo leer el archivo");
    reader.readAsText(file, "utf-8");
  };

  const apply = async () => {
    const days = preview.days.filter((d) => selected[d.date]).map((d) => ({ date: d.date, credits: d.real }));
    if (!days.length) return toast.warning("Selecciona al menos un día");
    setBusy(true);
    try {
      const { data } = await api.post("/cronos/reconcile/apply", { days });
      setResult(data);
      setPreview(null);
      qc.invalidateQueries();
      toast.success(`Cuadre aplicado: ${data.adjusted_entries} tareas ajustadas`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const nSel = Object.values(selected).filter(Boolean).length;

  return (
    <div className="space-y-4" data-testid="cuadrar-page">
      <div>
        <div className="mono-label">Cuadrar</div>
        <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Extracto real vs estimado</h1>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div
          className="panel p-4 lg:col-span-7"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files?.[0]); }}
          data-testid="reconcile-dropzone"
        >
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="mono-label">Pega el extracto de uso de Emergent o sube el CSV</div>
            {fileName && <span className="font-mono text-[11px] text-mint" data-testid="reconcile-file-name">{fileName}</span>}
          </div>
          <textarea
            data-testid="reconcile-paste-textarea"
            className="field h-48 resize-y py-2 font-mono text-xs leading-relaxed"
            placeholder={EXAMPLE}
            value={text}
            onChange={(e) => { setText(e.target.value); setFileName(""); }}
          />
          <input ref={fileRef} type="file" accept=".csv,.txt,text/csv,text/plain" className="hidden" data-testid="reconcile-file-input" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button data-testid="reconcile-parse-button" className="btn-primary" onClick={() => runPreview()} disabled={busy || !text.trim()}>
              <Search size={14} /> Vista previa
            </button>
            <button data-testid="reconcile-upload-button" className="btn-secondary" onClick={() => fileRef.current?.click()} disabled={busy}>
              <Upload size={14} /> Subir CSV
            </button>
            <button className="btn-secondary" onClick={() => { setText(EXAMPLE); setFileName(""); }} data-testid="reconcile-example-button">Usar ejemplo</button>
            <span className="font-mono text-[11px] text-slate-600">también puedes arrastrar el archivo aquí</span>
          </div>
        </div>
        <div className="panel p-4 lg:col-span-5">
          <div className="mono-label mb-2">Cómo funciona</div>
          <ul className="space-y-1.5 text-sm leading-relaxed text-slate-400">
            <li>· Se detectan fechas <span className="font-mono text-slate-200">AAAA-MM-DD</span> o <span className="font-mono text-slate-200">DD/MM/AAAA</span> y la cifra de créditos de cada línea (las horas tipo 12:30 se ignoran).</li>
            <li>· También puedes <span className="text-slate-200">subir el CSV</span> exportado de Emergent: se detectan las columnas de fecha y créditos por su cabecera (date/fecha, credits/créditos/coste…).</li>
            <li>· Se agrupa el gasto real por día y se compara con la suma estimada de las tareas de ese día.</li>
            <li>· Al aplicar, el gasto real se reparte <span className="text-slate-200">proporcionalmente</span> entre las tareas del día, que pasan a <span className="font-mono text-emerald-300">confirmado</span>. Si el día no tiene tareas se crea una entrada «Sin asignar».</li>
          </ul>
        </div>
      </div>

      {preview && (
        <div className="panel overflow-x-auto" data-testid="reconcile-preview">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-3">
            <div className="font-mono text-xs text-slate-400">
              <span className="mr-2 rounded-full border border-border px-1.5 py-px text-[10px] uppercase text-slate-500" data-testid="reconcile-format">{preview.format === "csv" ? "csv" : "texto"}</span>
              {preview.lines_parsed} líneas · {preview.days.length} días · real <span className="text-slate-100">{fmtCredits(preview.totals.real)}</span> vs estimado <span className="text-slate-100">{fmtCredits(preview.totals.estimated)}</span>
            </div>
            {isAdmin && (
              <button data-testid="apply-reconcile-button" className="btn-primary" onClick={apply} disabled={busy || nSel === 0}>
                <CheckCheck size={14} /> Aplicar cuadre ({nSel})
              </button>
            )}
          </div>
          <table className="w-full min-w-[720px]">
            <thead>
              <tr><th className="th w-10" /><th className="th">Día</th><th className="th text-right">Real</th><th className="th text-right">Estimado</th><th className="th text-right">Diferencia</th><th className="th text-right">Entradas</th><th className="th text-right">Confirmadas</th><th className="th">Estado</th></tr>
            </thead>
            <tbody>
              {preview.days.map((d) => (
                <tr key={d.date} className="hover:bg-surface-subtle/60" data-testid={`reconcile-day-${d.date}`}>
                  <td className="td">
                    <Checkbox data-testid={`reconcile-day-checkbox-${d.date}`} checked={Boolean(selected[d.date])} onCheckedChange={(v) => setSelected((s) => ({ ...s, [d.date]: Boolean(v) }))} className="border-slate-500 data-[state=checked]:border-mint data-[state=checked]:bg-mint data-[state=checked]:text-[#070B11]" />
                  </td>
                  <td className="td font-mono text-sm">{fmtDate(d.date)}</td>
                  <td className="td text-right font-mono text-sm font-semibold">{fmtCredits(d.real)}</td>
                  <td className="td text-right font-mono text-sm text-slate-400">{fmtCredits(d.estimated)}</td>
                  <td className={`td text-right font-mono text-sm font-semibold ${d.diff > 0 ? "text-red-400" : d.diff < 0 ? "text-emerald-400" : "text-slate-400"}`} data-testid={`reconcile-diff-${d.date}`}>
                    {d.diff > 0 ? "+" : ""}{fmtCredits(d.diff)}
                  </td>
                  <td className="td text-right font-mono text-xs">{d.entries}</td>
                  <td className="td text-right font-mono text-xs">{d.confirmed}</td>
                  <td className="td font-mono text-[11px]">
                    {d.entries === 0 ? <span className="text-cyan-300">creará «Sin asignar»</span> : d.already_imported ? <span className="text-amber-300">ya cuadrado · se recalculará</span> : <span className="text-slate-500">pendiente</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result && (
        <div className="panel border-mint/30 p-4" data-testid="reconcile-result">
          <div className="mono-label mb-2 text-mint">Cuadre aplicado</div>
          <div className="grid grid-cols-3 gap-4 font-mono">
            <div><div className="text-2xl font-bold">{result.days_applied.length}</div><div className="text-[11px] text-slate-500">días cuadrados</div></div>
            <div><div className="text-2xl font-bold text-mint" data-testid="reconcile-result-adjusted">{result.adjusted_entries}</div><div className="text-[11px] text-slate-500">tareas ajustadas</div></div>
            <div><div className="text-2xl font-bold text-cyan-300" data-testid="reconcile-result-unassigned">{result.unassigned_days.length}</div><div className="text-[11px] text-slate-500">días sin asignar</div></div>
          </div>
          {result.unassigned_days.length > 0 && <div className="mt-2 font-mono text-xs text-slate-400">Sin tareas: {result.unassigned_days.map(fmtDate).join(", ")}</div>}
        </div>
      )}

      <StatementsHistory />
    </div>
  );
}

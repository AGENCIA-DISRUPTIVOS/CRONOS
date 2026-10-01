import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Archive, ArchiveRestore, Mail, Plus, Save, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { fmtCredits, fmtEur } from "@/lib/format";
import { Light } from "@/components/SourceBadge";

function SettingsForm({ settings, onSaved }) {
  const [form, setForm] = useState({ price_per_credit_eur: "", monthly_budget_credits: "" });
  useEffect(() => {
    if (settings) setForm({ price_per_credit_eur: settings.price_per_credit_eur, monthly_budget_credits: settings.monthly_budget_credits });
  }, [settings]);
  const save = async (e) => {
    e.preventDefault();
    try {
      await api.put("/cronos/settings", { price_per_credit_eur: Number(form.price_per_credit_eur), monthly_budget_credits: Number(form.monthly_budget_credits) });
      toast.success("Ajustes guardados");
      onSaved();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  return (
    <form onSubmit={save} className="panel p-4" data-testid="settings-form">
      <div className="mono-label mb-3">Coste y presupuesto</div>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="mono-label">€ por crédito</span>
          <input data-testid="settings-price-input" type="number" step="0.0001" min="0" className="field font-mono" value={form.price_per_credit_eur} onChange={(e) => setForm((f) => ({ ...f, price_per_credit_eur: e.target.value }))} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="mono-label">Presupuesto mensual (cr)</span>
          <input data-testid="settings-budget-input" type="number" step="1" min="0" className="field font-mono" value={form.monthly_budget_credits} onChange={(e) => setForm((f) => ({ ...f, monthly_budget_credits: e.target.value }))} />
        </label>
      </div>
      <div className="mt-2 font-mono text-[11px] text-slate-500">
        Presupuesto equivalente: {fmtEur(Number(form.monthly_budget_credits) * Number(form.price_per_credit_eur))} · Avisos enviados este mes:{" "}
        {Object.entries(settings?.alerts_sent || {}).map(([m, v]) => `${m}: ${v.join("%, ")}%`).join(" · ") || "ninguno"}
      </div>
      <button className="btn-primary mt-3" data-testid="save-settings-button"><Save size={14} /> Guardar</button>
    </form>
  );
}

function Projects({ projects, onChange }) {
  const [draft, setDraft] = useState({ name: "", monthly_goal_credits: "", goal_credits: "", color: "#00FFBF" });
  const [edits, setEdits] = useState({});
  const num = (v) => (v === "" || v == null ? null : Number(v));
  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/cronos/projects", { ...draft, monthly_goal_credits: num(draft.monthly_goal_credits), goal_credits: num(draft.goal_credits) });
      toast.success("Proyecto creado");
      setDraft({ name: "", monthly_goal_credits: "", goal_credits: "", color: "#00FFBF" });
      onChange();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const patch = async (id, body, msg = "Proyecto actualizado") => {
    try {
      await api.patch(`/cronos/projects/${id}`, body);
      toast.success(msg);
      setEdits((s) => ({ ...s, [id]: undefined }));
      onChange();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const remove = async (p) => {
    if (!window.confirm(`¿Eliminar el proyecto «${p.name}»? Las entradas se conservan.`)) return;
    try {
      await api.delete(`/cronos/projects/${p.id}`);
      toast.success("Proyecto eliminado");
      onChange();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const ed = (p) => edits[p.id] || { monthly_goal_credits: p.monthly_goal_credits ?? "", goal_credits: p.goal_credits ?? "", color: p.color || "#00FFBF" };

  return (
    <div className="panel p-4" data-testid="projects-panel">
      <div className="mono-label mb-3">Proyectos y objetivos de créditos</div>
      <form onSubmit={create} className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-[1fr_140px_140px_60px_auto]">
        <input data-testid="project-name-input" className="field col-span-2 md:col-span-1" placeholder="Nombre del proyecto" required value={draft.name} onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))} />
        <input data-testid="project-monthly-goal-input" className="field font-mono" type="number" min="0" placeholder="Obj. mensual" value={draft.monthly_goal_credits} onChange={(e) => setDraft((d) => ({ ...d, monthly_goal_credits: e.target.value }))} />
        <input data-testid="project-total-goal-input" className="field font-mono" type="number" min="0" placeholder="Obj. total" value={draft.goal_credits} onChange={(e) => setDraft((d) => ({ ...d, goal_credits: e.target.value }))} />
        <input data-testid="project-color-input" className="field h-9 cursor-pointer p-1" type="color" value={draft.color} onChange={(e) => setDraft((d) => ({ ...d, color: e.target.value }))} />
        <button className="btn-primary" data-testid="project-create-button"><Plus size={14} /> Añadir</button>
      </form>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px]">
          <thead><tr><th className="th">Proyecto</th><th className="th text-right">Consumo total</th><th className="th text-right">Este mes</th><th className="th">Obj. mensual</th><th className="th">Obj. total</th><th className="th">Color</th><th className="th">Estado</th><th className="th" /></tr></thead>
          <tbody>
            {projects.map((p) => {
              const e = ed(p);
              const dirty = Boolean(edits[p.id]);
              return (
                <tr key={p.id} className={p.archived ? "opacity-50" : ""} data-testid={`project-row-${p.id}`}>
                  <td className="td text-sm">{p.name}{p.archived && <span className="ml-2 font-mono text-[10px] text-slate-500">archivado</span>}</td>
                  <td className="td text-right font-mono text-xs">{fmtCredits(p.consumed_total)}</td>
                  <td className="td text-right font-mono text-xs">{fmtCredits(p.consumed_month)}</td>
                  <td className="td"><input data-testid={`project-monthly-goal-${p.id}`} className="field h-8 w-28 font-mono text-xs" type="number" min="0" value={e.monthly_goal_credits} onChange={(ev) => setEdits((s) => ({ ...s, [p.id]: { ...e, monthly_goal_credits: ev.target.value } }))} /></td>
                  <td className="td"><input data-testid={`project-total-goal-${p.id}`} className="field h-8 w-28 font-mono text-xs" type="number" min="0" value={e.goal_credits} onChange={(ev) => setEdits((s) => ({ ...s, [p.id]: { ...e, goal_credits: ev.target.value } }))} /></td>
                  <td className="td"><input className="field h-8 w-10 cursor-pointer p-0.5" type="color" value={e.color} onChange={(ev) => setEdits((s) => ({ ...s, [p.id]: { ...e, color: ev.target.value } }))} /></td>
                  <td className="td"><Light status={p.status} /></td>
                  <td className="td">
                    <div className="flex justify-end gap-1">
                      {dirty && <button data-testid={`project-save-${p.id}`} className="btn-primary h-8 px-2 text-xs" onClick={() => patch(p.id, { monthly_goal_credits: num(e.monthly_goal_credits), goal_credits: num(e.goal_credits), color: e.color })}>Guardar</button>}
                      <button data-testid={`project-archive-${p.id}`} className="btn-ghost" title={p.archived ? "Restaurar" : "Archivar"} onClick={() => patch(p.id, { archived: !p.archived }, p.archived ? "Proyecto restaurado" : "Proyecto archivado")}>{p.archived ? <ArchiveRestore size={14} /> : <Archive size={14} />}</button>
                      <button data-testid={`project-delete-${p.id}`} className="btn-ghost hover:text-red-400" title="Eliminar" onClick={() => remove(p)}><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Digest({ settings }) {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/cronos/digest/send");
      setLast(data);
      toast.success(`Resumen enviado a ${data.sent_to.join(", ")}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="panel p-4" data-testid="digest-panel">
      <div className="mono-label mb-2">Recordatorio semanal</div>
      <p className="text-sm text-slate-400">Cada lunes a las 08:00 (Madrid) se envía el resumen de la semana anterior a: <span className="font-mono text-slate-200" data-testid="digest-recipients">{settings?.digest_recipients?.join(", ")}</span></p>
      <button data-testid="digest-send-now-button" className="btn-secondary mt-3" onClick={send} disabled={busy}><Mail size={14} /> {busy ? "Enviando…" : "Enviar ahora"}</button>
      {last && <div className="mt-2 font-mono text-[11px] text-slate-500" data-testid="digest-last-result">Periodo {last.period.from} → {last.period.to} · enviado a {last.sent_to.length}{last.failed.length ? ` · fallidos: ${last.failed.join(", ")}` : ""}</div>}
    </div>
  );
}

function AuditLog() {
  const { data: log = [] } = useQuery({ queryKey: ["audit"], queryFn: () => api.get("/cronos/audit").then((r) => r.data) });
  return (
    <div className="panel p-4" data-testid="audit-panel">
      <div className="mono-label mb-2">Auditoría · últimas acciones</div>
      <div className="max-h-72 space-y-1 overflow-y-auto font-mono text-[11px]">
        {log.map((a, i) => (
          <div key={i} className="flex gap-2 border-t border-border/50 py-1 text-slate-400">
            <span className="shrink-0 text-slate-600">{a.at?.slice(0, 16).replace("T", " ")}</span>
            <span className="shrink-0 text-mint">{a.action}</span>
            <span className="truncate">{a.who} · {a.detail}</span>
          </div>
        ))}
        {log.length === 0 && <div className="text-slate-600">sin registros</div>}
      </div>
    </div>
  );
}

export default function Ajustes() {
  const { isAdmin } = useAuth();
  const qc = useQueryClient();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get("/cronos/settings").then((r) => r.data), enabled: isAdmin });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.get("/cronos/projects").then((r) => r.data), enabled: isAdmin });
  if (!isAdmin) return <Navigate to="/" replace />;
  const refresh = () => qc.invalidateQueries();
  return (
    <div className="space-y-4" data-testid="ajustes-page">
      <div>
        <div className="mono-label">Ajustes</div>
        <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Configuración</h1>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SettingsForm settings={settings} onSaved={refresh} />
        <Digest settings={settings} />
      </div>
      <Projects projects={projects} onChange={refresh} />
      <AuditLog />
    </div>
  );
}

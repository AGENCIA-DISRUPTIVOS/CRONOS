import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BellRing, Copy, KeyRound, Plus, Power, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";

const copy = async (text, msg) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(msg);
  } catch {
    toast.error("No se ha podido copiar; selecciona el texto a mano");
  }
};

function StatusChip({ app }) {
  if (!app.enabled) return <span className="rounded-full border border-slate-600 px-2 py-0.5 font-mono text-[10px] text-slate-400">desactivada</span>;
  if (app.silent) return <span className="rounded-full border border-red-500/50 px-2 py-0.5 font-mono text-[10px] text-red-300">sin enviar</span>;
  if (!app.last_push_at) return <span className="rounded-full border border-amber-500/50 px-2 py-0.5 font-mono text-[10px] text-amber-300">esperando 1.º envío</span>;
  return <span className="rounded-full border border-mint/50 px-2 py-0.5 font-mono text-[10px] text-mint">recibiendo</span>;
}

function Reveal({ data, onClose }) {
  return (
    <div className="mb-4 rounded-md border border-amber-500/40 bg-amber-500/5 p-3" data-testid="app-reveal">
      <div className="mono-label mb-1 text-amber-300">Token de «{data.name}» · solo se muestra ahora</div>
      <div className="flex flex-wrap items-center gap-2">
        <code className="break-all rounded bg-surface-subtle px-2 py-1 font-mono text-xs" data-testid="app-reveal-token">{data.token}</code>
        <button className="btn-secondary" onClick={() => copy(data.token, "Token copiado")} data-testid="app-copy-token"><Copy size={14} /> Copiar token</button>
        <button className="btn-primary" onClick={() => copy(data.instructions, "Instrucciones copiadas: pégalas en el prompt de la app")} data-testid="app-copy-instructions"><Copy size={14} /> Copiar instrucciones</button>
        <button className="btn-ghost text-xs" onClick={onClose} data-testid="app-reveal-close">Ya lo he guardado</button>
      </div>
      <p className="mt-2 text-xs text-slate-400">Las instrucciones ya llevan el token y la URL de Cronos. Pégalas en el primer prompt de la app (o en su fichero de instrucciones del agente). Si lo pierdes, genera uno nuevo: el anterior deja de funcionar.</p>
      <textarea readOnly className="field mt-2 h-40 resize-y py-2 font-mono text-[11px]" value={data.instructions} data-testid="app-reveal-instructions" />
    </div>
  );
}

function CronLog() {
  const { data: log = [] } = useQuery({ queryKey: ["cron-log"], queryFn: () => api.get("/cronos/cron/log", { params: { limit: 12 } }).then((r) => r.data) });
  const color = (o) => ({ finished: "text-mint", accepted: "text-slate-300", error: "text-red-400", unauthorized: "text-red-400", duplicate_skipped: "text-amber-300" }[o] || "text-slate-400");
  return (
    <div className="mt-4" data-testid="cron-log">
      <div className="mono-label mb-1">Últimas llamadas del cron de la plataforma</div>
      <div className="max-h-44 space-y-1 overflow-y-auto font-mono text-[11px]">
        {log.map((l, i) => (
          <div key={`${l.at}-${i}`} className="flex gap-2 border-t border-border/50 py-1 text-slate-400">
            <span className="shrink-0 text-slate-600">{l.at?.slice(0, 16).replace("T", " ")}</span>
            <span className="shrink-0 text-slate-300">{l.cron}</span>
            <span className={`shrink-0 ${color(l.outcome)}`}>{l.outcome}</span>
            <span className="truncate">{l.detail}</span>
          </div>
        ))}
        {log.length === 0 && <div className="text-slate-600">Todavía no se ha registrado ninguna llamada. Si pasan las 07:30 y sigue vacío, el cron de la plataforma no está llamando.</div>}
      </div>
    </div>
  );
}

export function ConnectedApps() {
  const qc = useQueryClient();
  const { data: apps = [] } = useQuery({ queryKey: ["apps"], queryFn: () => api.get("/cronos/apps").then((r) => r.data) });
  const [form, setForm] = useState({ name: "", project: "" });
  const [reveal, setReveal] = useState(null);
  const [check, setCheck] = useState(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["apps"] });

  const create = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/cronos/apps", form);
      setReveal(data);
      setForm({ name: "", project: "" });
      refresh();
      qc.invalidateQueries({ queryKey: ["meta"] });
    } catch (err) { toast.error(errMsg(err)); }
  };
  const rotate = async (a) => {
    if (!window.confirm(`¿Generar un token nuevo para «${a.name}»? El actual dejará de funcionar y tendrás que pegar las instrucciones nuevas en la app.`)) return;
    try {
      const { data } = await api.post(`/cronos/apps/${a.id}/rotate`);
      setReveal(data);
      refresh();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const toggle = async (a) => {
    try {
      await api.patch(`/cronos/apps/${a.id}`, { enabled: !a.enabled });
      refresh();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const remove = async (a) => {
    if (!window.confirm(`¿Eliminar la app «${a.name}»? Sus tareas ya recibidas se conservan, pero dejará de poder enviar.`)) return;
    try {
      await api.delete(`/cronos/apps/${a.id}`);
      refresh();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const template = async () => {
    try {
      const { data } = await api.get("/cronos/apps/instructions-template");
      copy(data.markdown, "Plantilla copiada (con marcadores <TOKEN_DE_LA_APP>)");
    } catch (err) { toast.error(errMsg(err)); }
  };
  const runCheck = async (send) => {
    if (send && !window.confirm("¿Enviar ahora el aviso por email al responsable?")) return;
    try {
      const { data } = await api.post("/cronos/alerts/check", null, { params: { dry_run: !send } });
      setCheck(data);
      if (send) toast.success(data.sent.length ? `Aviso enviado a ${data.sent.join(", ")}` : "No había nada que avisar");
    } catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <div className="panel p-4" data-testid="connected-apps-panel">
      <div className="mono-label mb-1">Apps conectadas (envío directo a Cronos)</div>
      <p className="mb-3 text-xs text-slate-500">
        Cada app de Emergent envía sus tareas a Cronos al terminarlas, con su propio token: créditos, tokens, coste, usuario y un resumen que se convierte en su ficha de la wiki.
        La sincronización diaria de las 07:30 queda como respaldo. Si una app lleva más de 3 días sin enviar, o una fuente de respaldo falla, se avisa por email al responsable.
      </p>
      {reveal && <Reveal data={reveal} onClose={() => setReveal(null)} />}
      <form onSubmit={create} className="mb-3 grid gap-2 md:grid-cols-[1fr_1fr_auto_auto]">
        <input data-testid="app-name-input" className="field" placeholder="Nombre de la app (Asana Syncro)" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
        <input data-testid="app-project-input" className="field" placeholder="Proyecto en Cronos (por defecto, el nombre)" value={form.project} onChange={(e) => setForm((f) => ({ ...f, project: e.target.value }))} />
        <button className="btn-primary" data-testid="app-create-button"><Plus size={14} /> Conectar app</button>
        <button type="button" className="btn-secondary" onClick={template} data-testid="app-copy-template"><Copy size={14} /> Plantilla</button>
      </form>
      {apps.length === 0 ? <div className="font-mono text-xs text-slate-600" data-testid="apps-empty">Todavía no hay apps conectadas</div> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead><tr><th className="th">App</th><th className="th">Proyecto</th><th className="th">Estado</th><th className="th">Último envío</th><th className="th text-right">Tareas</th><th className="th">Token</th><th className="th" /></tr></thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id} data-testid={`app-row-${a.id}`} className={a.enabled ? "" : "opacity-60"}>
                  <td className="td text-sm">{a.name}</td>
                  <td className="td text-xs">{a.project}</td>
                  <td className="td"><StatusChip app={a} /></td>
                  <td className="td font-mono text-[11px] text-slate-400">{a.last_push_at ? `${a.last_push_at.slice(0, 16).replace("T", " ")} · ${(a.last_push_user || "").split("@")[0]}` : "nunca"}</td>
                  <td className="td text-right font-mono text-xs">{a.push_count || 0}</td>
                  <td className="td font-mono text-[11px] text-slate-500">{a.token_hint}</td>
                  <td className="td">
                    <div className="flex justify-end gap-1">
                      <button className="btn-ghost" title="Token nuevo + instrucciones" onClick={() => rotate(a)} data-testid={`app-rotate-${a.id}`}><KeyRound size={14} /></button>
                      <button className="btn-ghost" title={a.enabled ? "Desactivar" : "Activar"} onClick={() => toggle(a)} data-testid={`app-toggle-${a.id}`}><Power size={14} /></button>
                      <button className="btn-ghost hover:text-red-400" title="Eliminar" onClick={() => remove(a)} data-testid={`app-delete-${a.id}`}><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button className="btn-secondary" onClick={() => runCheck(false)} data-testid="alerts-check-button"><BellRing size={14} /> Revisar avisos (sin enviar)</button>
        <button className="btn-ghost text-xs" onClick={() => runCheck(true)} data-testid="alerts-send-button">Enviar aviso ahora</button>
        {check && (
          <span className="font-mono text-[11px] text-slate-400" data-testid="alerts-check-result">
            Destinatarios: {check.recipients.join(", ")} · apps sin enviar: {check.silent.length ? check.silent.join(", ") : "ninguna"}
          </span>
        )}
      </div>
      <CronLog />
    </div>
  );
}

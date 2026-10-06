import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export function SyncButton() {
  const { isAdmin } = useAuth();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const { data } = useQuery({ queryKey: ["sync-status"], queryFn: () => api.get("/cronos/sync/status").then((r) => r.data) });
  const last = data?.last_sync;
  const sync = async () => {
    setBusy(true);
    try {
      const { data: res } = await api.post("/cronos/sync");
      const ok = res.results.filter((r) => r.ok);
      const ko = res.results.filter((r) => !r.ok);
      const n = ok.reduce((a, r) => a + (r.entries || 0), 0);
      if (ok.length) toast.success(`Sincronizado: ${n} tareas de ${ok.length} fuente(s)`);
      ko.forEach((r) => toast.error(`${r.name}: ${r.error}`));
      qc.invalidateQueries();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  if (!isAdmin) return null;
  return (
    <div className="flex items-center gap-2" data-testid="sync-widget">
      {last && (
        <span className="hidden font-mono text-[11px] text-slate-500 md:inline" data-testid="sync-last" title={last.results?.map((r) => `${r.name}: ${r.ok ? `${r.entries} tareas` : r.error}`).join("\n")}>
          última sync {last.at?.slice(0, 16).replace("T", " ")} · {last.results?.filter((r) => r.ok).length}/{last.results?.length} OK
        </span>
      )}
      <button data-testid="sync-now-button" className="btn-secondary" onClick={sync} disabled={busy} title={data?.sources?.length ? `${data.sources.length} fuente(s)` : "Configura fuentes en Ajustes"}>
        <RefreshCw size={14} className={busy ? "animate-spin" : ""} /> {busy ? "Sincronizando…" : "Actualizar"}
      </button>
    </div>
  );
}

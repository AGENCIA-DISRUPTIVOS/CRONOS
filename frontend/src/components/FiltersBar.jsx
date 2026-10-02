import { X } from "lucide-react";

const FIELDS = [
  { key: "project", label: "Proyecto", metaKey: "projects" },
  { key: "user", label: "Usuario", metaKey: "users" },
  { key: "model", label: "Modelo", metaKey: "models" },
  { key: "type", label: "Tipo", metaKey: "types" },
  { key: "phase", label: "Fase", metaKey: "phases" },
  { key: "source", label: "Origen", metaKey: "sources" },
];

export const EMPTY_FILTERS = { project: "", user: "", model: "", type: "", phase: "", source: "", date_from: "", date_to: "" };

export function FiltersBar({ filters, setFilters, meta }) {
  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const dirty = Object.values(filters).some(Boolean);
  return (
    <div className="panel flex flex-wrap items-end gap-3 p-3" data-testid="filters-bar">
      {FIELDS.map(({ key, label, metaKey }) => (
        <label key={key} className="flex min-w-[130px] flex-1 flex-col gap-1 sm:flex-none">
          <span className="mono-label">{label}</span>
          <select data-testid={`filter-${key}-select`} className="field max-w-[200px] font-mono text-xs" value={filters[key]} onChange={(e) => set(key, e.target.value)}>
            <option value="">Todos</option>
            {(meta?.[metaKey] || []).map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </label>
      ))}
      <label className="flex flex-col gap-1">
        <span className="mono-label">Desde</span>
        <input data-testid="filter-date-from" type="date" className="field font-mono" value={filters.date_from} onChange={(e) => set("date_from", e.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="mono-label">Hasta</span>
        <input data-testid="filter-date-to" type="date" className="field font-mono" value={filters.date_to} onChange={(e) => set("date_to", e.target.value)} />
      </label>
      {dirty && (
        <button data-testid="filters-clear-button" className="btn-secondary" onClick={() => setFilters(EMPTY_FILTERS)}>
          <X size={14} /> Limpiar
        </button>
      )}
    </div>
  );
}

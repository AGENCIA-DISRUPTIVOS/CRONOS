export const fmtNum = (n, d = 0) =>
  new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d }).format(Number(n) || 0);
export const fmtCredits = (n) => fmtNum(n, Number.isInteger(Number(n)) ? 0 : 1);
export const fmtEur = (n) =>
  new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(Number(n) || 0);
export const fmtTokens = (n) => {
  const v = Number(n) || 0;
  if (v >= 1e6) return `${fmtNum(v / 1e6, 2)} M`;
  if (v >= 1e3) return `${fmtNum(v / 1e3, 1)} k`;
  return fmtNum(v);
};
export const fmtHours = (minutes) => `${fmtNum((Number(minutes) || 0) / 60, 1)} h`;
export const fmtDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
};
export const todayIso = () => new Date().toISOString().slice(0, 10);
export const TYPE_COLORS = {
  desarrollo: "#3B82F6",
  corrección: "#F97316",
  consulta: "#A855F7",
  pruebas: "#10B981",
};
export const PHASE_COLORS = ["#00FFBF", "#3B82F6", "#F97316", "#10B981", "#A855F7", "#06B6D4", "#F59E0B", "#64748B"];

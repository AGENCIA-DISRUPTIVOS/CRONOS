import { useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtCredits, fmtDate, fmtNum } from "@/lib/format";

const SERIES = [
  { key: "credits", label: "créditos", color: "#00FFBF", axis: "left" },
  { key: "minutes", label: "minutos", color: "#3B82F6", axis: "right" },
  { key: "messages", label: "mensajes", color: "#F97316", axis: "right" },
];

const TICK = { fill: "#64748B", fontSize: 11, fontFamily: "JetBrains Mono" };
const TICK_RIGHT = { ...TICK, fill: "#3B82F6" };
const MARGIN = { top: 4, right: -10, left: -20, bottom: 0 };
const TOOLTIP_STYLE = { background: "#0D131F", border: "1px solid #1E293B", borderRadius: 6, fontFamily: "JetBrains Mono", fontSize: 12 };
const DOT = { r: 3 };
const tooltipFormatter = (v, name) => {
  const s = SERIES.find((x) => x.key === name);
  return [name === "credits" ? `${fmtCredits(v)} cr` : fmtNum(v), s?.label || name];
};
const tickDate = (d) => fmtDate(d).slice(0, 5);

export function DailyChart({ daily }) {
  const [visible, setVisible] = useState({ credits: true, minutes: true, messages: true });
  const toggle = (k) => setVisible((v) => ({ ...v, [k]: !v[k] }));
  return (
    <div className="panel p-4" data-testid="daily-chart">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="mono-label">Consumo por día</div>
        <div className="flex gap-1.5">
          {SERIES.map((s) => (
            <button
              key={s.key}
              data-testid={`daily-chart-toggle-${s.key}`}
              onClick={() => toggle(s.key)}
              className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] transition-colors ${
                visible[s.key] ? "border-border bg-surface-subtle text-slate-200" : "border-transparent text-slate-600 line-through"
              }`}
            >
              <span className="h-2 w-2 rounded-full" style={{ background: s.color, opacity: visible[s.key] ? 1 : 0.3 }} />
              {s.label}
            </button>
          ))}
        </div>
      </div>
      {daily.length === 0 ? (
        <div className="flex h-56 items-center justify-center font-mono text-xs text-slate-600">sin datos</div>
      ) : (
        <div className="h-56 min-h-[224px] min-w-0">
          <ResponsiveContainer width="100%" height={224}>
            <ComposedChart data={daily} margin={MARGIN}>
              <defs>
                <linearGradient id="mintFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FFBF" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#00FFBF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tickFormatter={tickDate} tick={TICK} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" tick={TICK} axisLine={false} tickLine={false} />
              <YAxis yAxisId="right" orientation="right" tick={TICK_RIGHT} axisLine={false} tickLine={false} hide={!visible.minutes && !visible.messages} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={fmtDate} formatter={tooltipFormatter} />
              {visible.credits && <Area yAxisId="left" type="monotone" dataKey="credits" stroke="#00FFBF" strokeWidth={2} fill="url(#mintFill)" />}
              {visible.minutes && <Line yAxisId="right" type="monotone" dataKey="minutes" stroke="#3B82F6" strokeWidth={1.5} dot={DOT} />}
              {visible.messages && <Line yAxisId="right" type="monotone" dataKey="messages" stroke="#F97316" strokeWidth={1.5} strokeDasharray="4 3" dot={DOT} />}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

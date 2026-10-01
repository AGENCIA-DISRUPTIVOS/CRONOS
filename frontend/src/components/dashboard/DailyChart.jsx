import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtCredits, fmtDate } from "@/lib/format";

export function DailyChart({ daily }) {
  return (
    <div className="panel p-4" data-testid="daily-chart">
      <div className="mono-label mb-3">Créditos por día</div>
      {daily.length === 0 ? (
        <div className="flex h-56 items-center justify-center font-mono text-xs text-slate-600">sin datos</div>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={daily} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="mintFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FFBF" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#00FFBF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(d) => fmtDate(d).slice(0, 5)} tick={{ fill: "#64748B", fontSize: 11, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#64748B", fontSize: 11, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#0D131F", border: "1px solid #1E293B", borderRadius: 6, fontFamily: "JetBrains Mono", fontSize: 12 }}
                labelFormatter={fmtDate}
                formatter={(v, name) => [name === "credits" ? `${fmtCredits(v)} cr` : v, name === "credits" ? "créditos" : name]}
              />
              <Area type="monotone" dataKey="credits" stroke="#00FFBF" strokeWidth={2} fill="url(#mintFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

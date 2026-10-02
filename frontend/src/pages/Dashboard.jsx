import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, cleanParams } from "@/lib/api";
import { EMPTY_FILTERS, FiltersBar } from "@/components/FiltersBar";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { BudgetBar } from "@/components/dashboard/BudgetBar";
import { DailyChart } from "@/components/dashboard/DailyChart";
import { Breakdowns, Comparison, ModelUserBreakdowns } from "@/components/dashboard/Breakdowns";
import { TopTasks } from "@/components/dashboard/TopTasks";
import { ProjectCards } from "@/components/dashboard/ProjectCards";
import { MonthlyTrend } from "@/components/dashboard/MonthlyTrend";

export default function Dashboard() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: () => api.get("/cronos/meta").then((r) => r.data) });
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats", filters],
    queryFn: () => api.get("/cronos/stats", { params: cleanParams(filters) }).then((r) => r.data),
  });
  const { data: budget } = useQuery({ queryKey: ["budget"], queryFn: () => api.get("/cronos/budget").then((r) => r.data) });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.get("/cronos/projects").then((r) => r.data) });
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api.get("/cronos/settings").then((r) => r.data) });

  return (
    <div className="space-y-5" data-testid="dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mono-label">Panel de costes</div>
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Consumo de agentes IA</h1>
        </div>
      </div>
      <FiltersBar filters={filters} setFilters={setFilters} meta={meta} />
      {isLoading || !stats ? (
        <div className="font-mono text-xs text-slate-500" data-testid="stats-loading">cargando estadísticas…</div>
      ) : (
        <>
          <KpiCards stats={stats} />
          <BudgetBar budget={budget} />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="lg:col-span-8"><DailyChart daily={stats.daily} /></div>
            <div className="lg:col-span-4"><Comparison comparison={stats.comparison} /></div>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Breakdowns stats={stats} phaseGoals={settings?.phase_goals} />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <ModelUserBreakdowns stats={stats} />
          </div>
          <MonthlyTrend monthly={stats.monthly || []} />
          <TopTasks top={stats.top} price={stats.price_per_credit_eur} />
          <ProjectCards projects={projects} />
        </>
      )}
    </div>
  );
}

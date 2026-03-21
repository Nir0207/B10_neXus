"use client";

import { memo, startTransition, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsService, type TrendAnalyticsResponse } from "@/services/analyticsService";
import { exportToPharmaHTML } from "@/utils/HtmlExporter";

const DISEASE_SUGGESTIONS = [
  "Lung cancer",
  "Breast cancer",
  "Ovarian cancer",
  "Alzheimer's disease",
] as const;

const AXIS_COLOR = "#8c919d";
const GRID_COLOR = "rgba(140, 145, 157, 0.14)";
const PRIMARY_LINE = "#81cfff";
const SECONDARY_LINE = "#ffba2c";
const TOOLTIP_STYLE = {
  backgroundColor: "rgba(25, 28, 34, 0.96)",
  border: "1px solid rgba(129, 207, 255, 0.18)",
  borderRadius: "18px",
  color: "#e1e2eb",
};

type ActiveChart = "line" | "bar" | "radar";

interface ChartCardProps {
  active: boolean;
  children: React.ReactNode;
  eyebrow: string;
  subtitle: string;
  title: string;
  onClick: () => void;
}

interface InsightCardProps {
  label: string;
  value: string;
  detail: string;
}

const ChartCard = memo(function ChartCard({
  active,
  children,
  eyebrow,
  subtitle,
  title,
  onClick,
}: ChartCardProps): React.JSX.Element {
  return (
    <button
      className={`group relative overflow-hidden rounded-[30px] border p-5 text-left shadow-2xl transition-all ${
        active
          ? "border-primary/35 bg-surface-container-high ring-1 ring-primary/25"
          : "border-outline-variant/15 bg-surface-container-low hover:border-primary/20 hover:bg-surface-container"
      }`}
      onClick={onClick}
      type="button"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(129,207,255,0.14),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_50%)]" />
      <div className="relative">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-[0.28em] text-primary">{eyebrow}</p>
            <h2 className="text-lg font-headline font-semibold text-on-surface">{title}</h2>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] ${
              active
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-outline-variant/15 bg-surface-container-lowest text-on-surface-variant"
            }`}
          >
            {subtitle}
          </span>
        </div>
        <div className="h-80 w-full">{children}</div>
      </div>
    </button>
  );
});

const InsightCard = memo(function InsightCard({
  label,
  value,
  detail,
}: InsightCardProps): React.JSX.Element {
  return (
    <article className="relative overflow-hidden rounded-[26px] border border-outline-variant/15 bg-surface-container-low p-5 shadow-xl">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(129,207,255,0.14),_transparent_38%)]" />
      <div className="relative">
        <p className="text-[10px] uppercase tracking-[0.26em] text-on-surface-variant">{label}</p>
        <p className="mt-3 text-3xl font-headline font-bold text-on-surface">{value}</p>
        <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">{detail}</p>
      </div>
    </article>
  );
});

function toExportPayload(data: TrendAnalyticsResponse, activeChart: ActiveChart) {
  if (activeChart === "radar") {
    return {
      chart_type: "radar" as const,
      title: `${data.disease_name} Organ Affinity`,
      disease_id: data.disease_id,
      disease_name: data.disease_name,
      datasets: data.organ_affinity.map((row) => ({ ...row })),
      clinical_summary: data.clinical_summary,
      x_key: "organ",
      y_key: "value",
    };
  }

  if (activeChart === "bar") {
    return {
      chart_type: "bar" as const,
      title: `${data.disease_name} Gene Distribution`,
      disease_id: data.disease_id,
      disease_name: data.disease_name,
      datasets: data.gene_distribution.map((row) => ({ ...row })),
      clinical_summary: data.clinical_summary,
      x_key: "gene_symbol",
      y_key: "association_score",
    };
  }

  return {
    chart_type: "line" as const,
    title: `${data.disease_name} Study Frequency`,
    disease_id: data.disease_id,
    disease_name: data.disease_name,
    datasets: data.frequency_timeline.map((row) => ({ ...row })),
    clinical_summary: data.clinical_summary,
    x_key: "year",
    y_key: "study_count",
  };
}

function TrendDashboardContent(): React.JSX.Element {
  const [draftDisease, setDraftDisease] = useState<string>("Lung cancer");
  const [selectedDisease, setSelectedDisease] = useState<string>("Lung cancer");
  const [activeChart, setActiveChart] = useState<ActiveChart>("line");
  const [data, setData] = useState<TrendAnalyticsResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;

    setError("");
    setIsLoading(data === null);
    setIsRefreshing(data !== null);

    void analyticsService
      .fetchTrends(selectedDisease, controller.signal)
      .then((response) => {
        startTransition(() => {
          setData(response);
        });
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load disease trends.");
      })
      .finally(() => {
        if (controller.signal.aborted) {
          return;
        }
        setIsLoading(false);
        setIsRefreshing(false);
      });

    return () => {
      controller.abort();
    };
  }, [selectedDisease]);

  const deferredTimeline = useDeferredValue(data?.frequency_timeline ?? []);
  const deferredGenes = useDeferredValue(data?.gene_distribution ?? []);
  const deferredAffinity = useDeferredValue(data?.organ_affinity ?? []);
  const exportPayload = useMemo(
    () => (data ? toExportPayload(data, activeChart) : null),
    [activeChart, data]
  );
  const timelineStudyCount = useMemo(
    () => deferredTimeline.reduce((total, point) => total + point.study_count, 0),
    [deferredTimeline]
  );
  const firstYear = deferredTimeline[0]?.year;
  const lastYear = deferredTimeline[deferredTimeline.length - 1]?.year;
  const topGene = deferredGenes[0];
  const radarMinWidth = Math.max(780, deferredAffinity.length * 110);

  return (
    <div className="panel-scrollbar relative flex-1 min-h-0 overflow-y-auto bg-background">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute top-[-10%] right-[-5%] h-[34rem] w-[34rem] rounded-full bg-primary/10 blur-[130px]" />
        <div className="absolute left-[-12%] top-[28%] h-[28rem] w-[28rem] rounded-full bg-tertiary/8 blur-[120px]" />
        <div className="absolute bottom-[-18%] right-[14%] h-[26rem] w-[26rem] rounded-full bg-primary-container/18 blur-[120px]" />
      </div>

      <div className="relative mx-auto flex max-w-[1520px] gap-6 px-6 py-8">
        <aside className="sticky top-6 h-fit w-[21.5rem] shrink-0 overflow-hidden rounded-[34px] border border-outline-variant/15 bg-surface-container-low/95 p-6 shadow-2xl backdrop-blur-xl">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(129,207,255,0.16),_transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_60%)]" />
          <div className="relative">
            <p className="mb-2 text-[10px] uppercase tracking-[0.3em] text-primary">Historical Trends</p>
            <h1 className="text-3xl font-headline font-bold tracking-tight text-on-surface">
              Disease Intelligence
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-on-surface-variant">
              Track study acceleration, target pressure, and tissue affinity from the local refinery without leaving
              the portal.
            </p>

            <div className="mt-6 rounded-[28px] border border-primary/15 bg-background/70 p-4">
              <p className="text-[10px] uppercase tracking-[0.26em] text-on-surface-variant">Signal Focus</p>
              <p className="mt-3 text-lg font-headline font-semibold text-on-surface">
                {data?.disease_name ?? selectedDisease}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  firstYear && lastYear ? `${firstYear} to ${lastYear}` : "Awaiting timeline",
                  topGene ? `Lead gene ${topGene.gene_symbol}` : "Gene rank pending",
                  `${data?.therapeutic_landscape.length ?? 0} active molecules`,
                ].map((chip) => (
                  <span
                    className="rounded-full border border-outline-variant/15 bg-surface-container-low px-3 py-1.5 text-[11px] font-medium text-on-surface-variant"
                    key={chip}
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </div>

            <form
              className="mt-6 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                setSelectedDisease(draftDisease.trim() || "Lung cancer");
              }}
            >
              <label className="block text-[10px] uppercase tracking-[0.22em] text-on-surface-variant" htmlFor="disease-query">
                Disease
              </label>
              <input
                id="disease-query"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm text-on-surface outline-none transition focus:border-primary/45"
                onChange={(event) => setDraftDisease(event.target.value)}
                placeholder="Search disease intelligence"
                value={draftDisease}
              />
              <button
                className="w-full rounded-2xl bg-gradient-to-br from-primary to-primary-container px-4 py-3 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90"
                type="submit"
              >
                Load Trends
              </button>
            </form>

            <div className="mt-5 flex flex-wrap gap-2">
              {DISEASE_SUGGESTIONS.map((suggestion) => (
                <button
                  className={`rounded-full border px-3 py-1.5 text-[11px] font-medium transition ${
                    selectedDisease === suggestion
                      ? "border-primary/35 bg-primary/12 text-primary"
                      : "border-outline-variant/15 bg-surface-container-low text-on-surface-variant hover:border-primary/25 hover:text-primary"
                  }`}
                  key={suggestion}
                  onClick={() => {
                    setDraftDisease(suggestion);
                    setSelectedDisease(suggestion);
                  }}
                  type="button"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            <div className="mt-8 overflow-hidden rounded-[28px] border border-primary/20 bg-gradient-to-br from-primary/12 via-surface-container-high to-surface-container-low p-5">
              <p className="text-[10px] uppercase tracking-[0.24em] text-primary">Export Engine</p>
              <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">
                Package the active visual and its source matrix into a standalone offline HTML report.
              </p>
              <button
                className="mt-4 w-full rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={exportPayload === null}
                onClick={() => {
                  if (exportPayload === null) {
                    return;
                  }
                  void exportToPharmaHTML(exportPayload);
                }}
                type="button"
              >
                Export Report
              </button>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 space-y-6 pb-8">
          <section className="relative overflow-hidden rounded-[34px] border border-outline-variant/15 bg-surface-container-low/95 p-7 shadow-2xl backdrop-blur-xl">
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(129,207,255,0.12),transparent_45%),radial-gradient(circle_at_top_right,rgba(255,186,44,0.1),transparent_22%)]" />
            <div className="relative flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-4xl">
                <p className="text-[10px] uppercase tracking-[0.3em] text-primary">Analytics Gateway</p>
                <h2 className="mt-3 text-4xl font-headline font-bold tracking-tight text-on-surface">
                  {data?.disease_name ?? selectedDisease}
                </h2>
                <p className="mt-4 max-w-3xl text-sm leading-relaxed text-on-surface-variant">
                  {data?.clinical_summary ?? "Loading local disease intelligence from the refinery."}
                </p>
              </div>
              <div className="rounded-2xl border border-outline-variant/15 bg-background/70 px-4 py-3 text-sm text-on-surface-variant">
                {isRefreshing ? "Refreshing dataset" : isLoading ? "Loading dataset" : "Live from Postgres"}
              </div>
            </div>
          </section>

          {error ? (
            <section className="rounded-[28px] border border-error/25 bg-error-container/20 px-5 py-4 text-sm text-on-error-container">
              {error}
            </section>
          ) : null}

          <section className="grid gap-4 xl:grid-cols-4">
            <InsightCard
              detail={firstYear && lastYear ? `Captured from ${firstYear} through ${lastYear}.` : "Timeline loads after the first successful query."}
              label="Study Span"
              value={deferredTimeline.length > 0 ? `${deferredTimeline.length} yrs` : "--"}
            />
            <InsightCard
              detail="Total unique study references aggregated from the lake."
              label="Study Volume"
              value={timelineStudyCount > 0 ? timelineStudyCount.toLocaleString() : "--"}
            />
            <InsightCard
              detail={topGene ? `UniProt ${topGene.uniprot_id}` : "Waiting for ranked target evidence."}
              label="Lead Target"
              value={topGene?.gene_symbol ?? "--"}
            />
            <InsightCard
              detail="ChEMBL active molecules linked to the top target set."
              label="Therapeutic Landscape"
              value={`${data?.therapeutic_landscape.length ?? 0}`}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <ChartCard
              active={activeChart === "line"}
              eyebrow="Study Frequency"
              onClick={() => setActiveChart("line")}
              subtitle="NCBI Timeline"
              title="Study Frequency vs Year"
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={deferredTimeline}>
                  <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                  <XAxis dataKey="year" stroke={AXIS_COLOR} tickLine={false} />
                  <YAxis stroke={AXIS_COLOR} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: PRIMARY_LINE, strokeOpacity: 0.18 }} />
                  <Line
                    type="monotone"
                    dataKey="study_count"
                    stroke={PRIMARY_LINE}
                    strokeWidth={3}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              active={activeChart === "bar"}
              eyebrow="Target Ranking"
              onClick={() => setActiveChart("bar")}
              subtitle="Open Targets"
              title="Gene Association Score"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deferredGenes}>
                  <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                  <XAxis dataKey="gene_symbol" stroke={AXIS_COLOR} tickLine={false} />
                  <YAxis stroke={AXIS_COLOR} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgba(129, 207, 255, 0.08)" }} />
                  <Bar dataKey="association_score" fill={PRIMARY_LINE} radius={[10, 10, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <div className="xl:col-span-2">
              <ChartCard
                active={activeChart === "radar"}
                eyebrow="Tissue Affinity"
                onClick={() => setActiveChart("radar")}
                subtitle="Scrollable"
                title="UniProt Tissue Specificity Affinity"
              >
                <div className="grid h-full gap-4 xl:grid-cols-[minmax(0,1fr)_260px]">
                  <div className="panel-scrollbar overflow-x-auto overflow-y-hidden rounded-[22px] border border-outline-variant/15 bg-background/50 px-4 py-4">
                    <div style={{ width: `${radarMinWidth}px`, height: "100%" }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" data={deferredAffinity} outerRadius="70%">
                          <PolarGrid stroke="rgba(129, 207, 255, 0.2)" />
                          <PolarAngleAxis dataKey="organ" stroke="#c2c6d4" tick={{ fill: "#c2c6d4", fontSize: 12 }} />
                          <PolarRadiusAxis
                            angle={30}
                            axisLine={false}
                            domain={[0, "auto"]}
                            stroke="#8c919d"
                            tick={{ fill: "#8c919d", fontSize: 11 }}
                          />
                          <Radar
                            dataKey="value"
                            stroke={SECONDARY_LINE}
                            fill={SECONDARY_LINE}
                            fillOpacity={0.26}
                            isAnimationActive={false}
                          />
                          <Tooltip contentStyle={TOOLTIP_STYLE} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="rounded-[22px] border border-outline-variant/15 bg-background/45 p-4">
                    <p className="text-[10px] uppercase tracking-[0.24em] text-primary">Affinity Highlights</p>
                    <div className="panel-scrollbar mt-4 max-h-56 space-y-3 overflow-y-auto pr-2">
                      {deferredAffinity.length > 0 ? (
                        deferredAffinity.map((point, index) => (
                          <div
                            className="rounded-2xl border border-outline-variant/15 bg-surface-container-low px-4 py-3"
                            key={`${point.organ}-${index}`}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-sm font-semibold text-on-surface">{point.organ}</p>
                              <span className="rounded-full bg-primary/12 px-2.5 py-1 text-[11px] font-semibold text-primary">
                                {point.value}
                              </span>
                            </div>
                            <div className="mt-3 h-2 rounded-full bg-surface-container-high">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-primary to-tertiary"
                                style={{ width: `${Math.min(point.value * 100, 100)}%` }}
                              />
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-on-surface-variant">No tissue affinity values available yet.</p>
                      )}
                    </div>
                    <p className="mt-4 text-xs leading-relaxed text-on-surface-variant">
                      Scroll horizontally in the radar canvas when tissue labels extend beyond the visible frame.
                    </p>
                  </div>
                </div>
              </ChartCard>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default function TrendDashboard(): React.JSX.Element {
  return (
    <AuthGuard>
      <TrendDashboardContent />
    </AuthGuard>
  );
}

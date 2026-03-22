"use client";

import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "@/components/AuthProvider";
import {
  fetchTelemetryDashboard,
  type MetricBucket,
  type TelemetryDashboardPayload,
} from "@/services/telemetryService";
import { exportToPharmaHTML } from "@/utils/HtmlExporter";

const RANGE_OPTIONS: readonly number[] = [7, 14, 30];
const PIE_COLORS: readonly string[] = ["#2563eb", "#0f766e", "#ea580c", "#7c3aed", "#0891b2"];

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}): React.JSX.Element {
  return (
    <div className="rounded-[1.75rem] border border-outline-variant/15 bg-surface-container-low/90 p-5 shadow-xl">
      <p className="text-[10px] uppercase tracking-[0.28em] text-primary">{label}</p>
      <p className="mt-3 text-3xl font-black text-on-surface">{value}</p>
      <p className="mt-2 text-sm text-on-surface-variant">{detail}</p>
    </div>
  );
}

function ChartCard({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section className="rounded-[1.75rem] border border-outline-variant/15 bg-surface-container-low/90 p-6 shadow-xl">
      <p className="text-[10px] uppercase tracking-[0.28em] text-primary">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-headline font-bold text-on-surface">{title}</h2>
      <div className="mt-5 h-80">{children}</div>
    </section>
  );
}

function EmptyState({ message }: { message: string }): React.JSX.Element {
  return (
    <div className="flex h-64 items-center justify-center rounded-[1.75rem] border border-dashed border-outline-variant/25 bg-background/60 p-6 text-center text-sm text-on-surface-variant">
      {message}
    </div>
  );
}

export default function TelemetryDashboard(): React.JSX.Element {
  const { session } = useAuth();
  const [rangeDays, setRangeDays] = useState<number>(7);
  const [dashboard, setDashboard] = useState<TelemetryDashboardPayload | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    void fetchTelemetryDashboard(rangeDays, session?.token)
      .then((response: TelemetryDashboardPayload) => {
        if (!isMounted) {
          return;
        }

        startTransition(() => {
          setDashboard(response);
        });
      })
      .catch((error: unknown) => {
        if (!isMounted) {
          return;
        }

        setErrorMessage(error instanceof Error ? error.message : "Telemetry dashboard unavailable.");
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [rangeDays, session?.token]);

  const deferredDailyActivity = useDeferredValue(dashboard?.dailyActivity ?? []);
  const deferredEventComparison = useDeferredValue(dashboard?.eventComparison ?? []);
  const deferredRouteComparison = useDeferredValue(dashboard?.routeComparison.slice(0, 6) ?? []);
  const deferredBrowserComparison = useDeferredValue(dashboard?.browserComparison ?? []);
  const deferredDeviceComparison = useDeferredValue(dashboard?.deviceComparison ?? []);
  const recentEvents = useDeferredValue(dashboard?.recentEvents ?? []);
  const exportPayload = useMemo(() => {
    if (!dashboard) {
      return null;
    }

    const hasDailyActivity = dashboard.dailyActivity.length > 0;
    const datasets = hasDailyActivity
      ? dashboard.dailyActivity.map((point) => ({
          date: point.date,
          total_events: point.totalEvents,
          unique_users: point.uniqueUsers,
          admin_events: point.adminEvents,
          non_admin_events: point.nonAdminEvents,
        }))
      : dashboard.eventComparison.map((bucket) => ({
          event_type: bucket.key,
          event_count: bucket.count,
        }));

    return {
      chart_type: hasDailyActivity ? ("line" as const) : ("bar" as const),
      title: hasDailyActivity
        ? `Telemetry Activity - Last ${dashboard.rangeDays} Days`
        : `Telemetry Event Comparison - Last ${dashboard.rangeDays} Days`,
      disease_id: `telemetry-${dashboard.rangeDays}-days`,
      disease_name: "Portal Telemetry",
      datasets,
      clinical_summary:
        `Telemetry snapshot for the last ${dashboard.rangeDays} days. ` +
        `Total events: ${dashboard.totalEvents}. ` +
        `Unique users: ${dashboard.uniqueUsers}. ` +
        `Active routes: ${dashboard.activeRoutes}. ` +
        `Average events per user: ${dashboard.averageEventsPerUser.toFixed(2)}.`,
      x_key: hasDailyActivity ? "date" : "event_type",
      y_key: hasDailyActivity ? "total_events" : "event_count",
      report_id: `BNX-TELEMETRY-${dashboard.rangeDays}D`,
      model_name: "BioNexus Telemetry Engine",
    };
  }, [dashboard]);

  const generatedLabel = dashboard?.generatedAt
    ? new Date(dashboard.generatedAt).toLocaleString()
    : "Waiting for telemetry";

  if (isLoading && !dashboard) {
    return <EmptyState message="Loading comparative telemetry metrics from the GraphQL service." />;
  }

  if (errorMessage && !dashboard) {
    return <EmptyState message={errorMessage} />;
  }

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
        <section className="overflow-hidden rounded-[2rem] border border-outline-variant/15 bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.18),_transparent_38%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(15,118,110,0.7))] p-7 text-white shadow-2xl">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-[10px] uppercase tracking-[0.32em] text-sky-100/90">Admin Telemetry</p>
              <h1 className="mt-3 text-4xl font-headline font-black leading-tight">
                Comparative portal telemetry for authenticated BioNexus sessions.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-200">
                This dashboard compares route traffic, event mix, browser spread, and admin vs
                researcher behavior from the new Mongo-backed GraphQL telemetry stream.
              </p>
            </div>

            <div className="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur-md">
              <p className="text-[10px] uppercase tracking-[0.24em] text-slate-200">Operator</p>
              <p className="mt-2 text-lg font-bold">{session?.fullName || session?.username}</p>
              <p className="text-sm text-slate-200">{generatedLabel}</p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            {RANGE_OPTIONS.map((option: number) => {
              const isActive = option === rangeDays;
              return (
                <button
                  className={
                    isActive
                      ? "rounded-full bg-white px-4 py-2 text-xs font-bold text-slate-950"
                      : "rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold text-white/85 transition-colors hover:bg-white/20"
                  }
                  data-telemetry-label={`range-${option}-days`}
                  key={option}
                  onClick={() => {
                    setIsLoading(true);
                    setErrorMessage("");
                    setRangeDays(option);
                  }}
                  type="button"
                >
                  Last {option} days
                </button>
              );
            })}
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total Events"
            value={String(dashboard?.totalEvents ?? 0)}
            detail="Captured page views and interaction events from logged-in sessions."
          />
          <MetricCard
            label="Unique Users"
            value={String(dashboard?.uniqueUsers ?? 0)}
            detail="Distinct authenticated users represented in the current range."
          />
          <MetricCard
            label="Active Routes"
            value={String(dashboard?.activeRoutes ?? 0)}
            detail="Routes with telemetry activity in the selected window."
          />
          <MetricCard
            label="Avg / User"
            value={(dashboard?.averageEventsPerUser ?? 0).toFixed(2)}
            detail="Mean event density for each active authenticated user."
          />
        </section>

        <section className="overflow-hidden rounded-[1.75rem] border border-primary/15 bg-gradient-to-br from-primary/12 via-surface-container-high to-surface-container-low p-6 shadow-xl">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary">Export Engine</p>
              <h2 className="mt-2 text-2xl font-headline font-bold text-on-surface">
                Export the telemetry snapshot as standalone HTML
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-on-surface-variant">
                Package the active telemetry comparison into an offline HTML report with chart data,
                summary metrics, and the underlying source matrix.
              </p>
            </div>

            <button
              className="rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              data-telemetry-label="export-telemetry-report"
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
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
          <ChartCard eyebrow="Flow" title="Daily activity and user mix">
            {deferredDailyActivity.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={deferredDailyActivity}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748b" tickLine={false} />
                  <YAxis stroke="#64748b" tickLine={false} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="totalEvents"
                    name="Total Events"
                    stroke="#2563eb"
                    strokeWidth={2.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="adminEvents"
                    name="Admin Events"
                    stroke="#0f766e"
                    strokeWidth={2.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="nonAdminEvents"
                    name="Non-Admin Events"
                    stroke="#ea580c"
                    strokeWidth={2.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No telemetry events have been recorded for the selected range yet." />
            )}
          </ChartCard>

          <ChartCard eyebrow="Segments" title="Admin vs non-admin traffic">
            {dashboard?.userSegmentComparison.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dashboard.userSegmentComparison}
                    dataKey="count"
                    nameKey="key"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={4}
                    isAnimationActive={false}
                  >
                    {dashboard.userSegmentComparison.map((entry: MetricBucket, index: number) => (
                      <Cell fill={PIE_COLORS[index % PIE_COLORS.length]} key={entry.key} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="User-segment comparison will appear after the first authenticated events arrive." />
            )}
          </ChartCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <ChartCard eyebrow="Events" title="Event type comparison">
            {deferredEventComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deferredEventComparison}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
                  <XAxis dataKey="key" stroke="#64748b" tickLine={false} />
                  <YAxis stroke="#64748b" tickLine={false} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2563eb" radius={[10, 10, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="Event comparison will populate once the portal starts sending telemetry." />
            )}
          </ChartCard>

          <ChartCard eyebrow="Routes" title="Most active routes">
            {deferredRouteComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deferredRouteComparison} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" tickLine={false} allowDecimals={false} />
                  <YAxis dataKey="key" type="category" stroke="#64748b" tickLine={false} width={110} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0f766e" radius={[0, 10, 10, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="Route comparison appears after page-view traffic is recorded." />
            )}
          </ChartCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <ChartCard eyebrow="Clients" title="Browser distribution">
            {deferredBrowserComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deferredBrowserComparison}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
                  <XAxis dataKey="key" stroke="#64748b" tickLine={false} />
                  <YAxis stroke="#64748b" tickLine={false} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#7c3aed" radius={[10, 10, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="Browser distribution needs at least one tracked client session." />
            )}
          </ChartCard>

          <ChartCard eyebrow="Devices" title="Device profile comparison">
            {deferredDeviceComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={deferredDeviceComparison}
                    dataKey="count"
                    nameKey="key"
                    innerRadius={55}
                    outerRadius={100}
                    paddingAngle={4}
                    isAnimationActive={false}
                  >
                    {deferredDeviceComparison.map((entry: MetricBucket, index: number) => (
                      <Cell fill={PIE_COLORS[index % PIE_COLORS.length]} key={entry.key} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="Device mix will appear after mobile, tablet, or desktop visits are tracked." />
            )}
          </ChartCard>
        </section>

        <section className="rounded-[1.75rem] border border-outline-variant/15 bg-surface-container-low/90 p-6 shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary">Recent Events</p>
              <h2 className="mt-2 text-xl font-headline font-bold text-on-surface">
                Latest authenticated client signals
              </h2>
            </div>
            <p className="text-sm text-on-surface-variant">
              Browser, route, and event-type slices update from the same Mongo telemetry stream.
            </p>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full divide-y divide-outline-variant/10 text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">
                  <th className="px-3 py-3 font-medium">User</th>
                  <th className="px-3 py-3 font-medium">Role</th>
                  <th className="px-3 py-3 font-medium">Event</th>
                  <th className="px-3 py-3 font-medium">Route</th>
                  <th className="px-3 py-3 font-medium">Browser</th>
                  <th className="px-3 py-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/10">
                {recentEvents.length > 0 ? (
                  recentEvents.map((event) => (
                    <tr className="text-on-surface" key={event.id}>
                      <td className="px-3 py-3 font-semibold">{event.username}</td>
                      <td className="px-3 py-3">{event.isAdmin ? "Admin" : "Researcher"}</td>
                      <td className="px-3 py-3">{event.label || event.eventType}</td>
                      <td className="px-3 py-3 text-on-surface-variant">{event.route || "n/a"}</td>
                      <td className="px-3 py-3 text-on-surface-variant">{event.browserName || "Unknown"}</td>
                      <td className="px-3 py-3 text-on-surface-variant">
                        {new Date(event.createdAt).toLocaleString()}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-on-surface-variant" colSpan={6}>
                      No recent events captured yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

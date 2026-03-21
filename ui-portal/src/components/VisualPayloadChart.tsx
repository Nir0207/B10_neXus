"use client";

import { memo, useDeferredValue } from "react";
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
import type { VisualPayload } from "@/services/intelligenceService";

interface Props {
  payload: VisualPayload;
}

function VisualPayloadChartComponent({ payload }: Props): React.JSX.Element {
  const datasets = useDeferredValue(payload.datasets);

  return (
    <div className="mt-3 rounded-2xl border border-primary/15 bg-surface-container-low p-3">
      <div className="mb-3">
        <p className="text-xs font-semibold text-on-surface">{payload.title}</p>
        <p className="text-[10px] uppercase tracking-[0.22em] text-on-surface-variant">
          {payload.disease_name}
        </p>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {payload.chart_type === "line" ? (
            <LineChart data={datasets}>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
              <XAxis dataKey={payload.x_key} stroke="#64748b" tickLine={false} />
              <YAxis stroke="#64748b" tickLine={false} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey={payload.y_key}
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          ) : payload.chart_type === "radar" ? (
            <RadarChart data={datasets}>
              <PolarGrid />
              <PolarAngleAxis dataKey={payload.x_key} />
              <PolarRadiusAxis />
              <Radar
                dataKey={payload.y_key}
                stroke="#2563eb"
                fill="#2563eb"
                fillOpacity={0.35}
                isAnimationActive={false}
              />
              <Tooltip />
            </RadarChart>
          ) : (
            <BarChart data={datasets}>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
              <XAxis dataKey={payload.x_key} stroke="#64748b" tickLine={false} />
              <YAxis stroke="#64748b" tickLine={false} />
              <Tooltip />
              <Bar dataKey={payload.y_key} fill="#2563eb" radius={[8, 8, 0, 0]} isAnimationActive={false} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

const VisualPayloadChart = memo(VisualPayloadChartComponent);

export default VisualPayloadChart;

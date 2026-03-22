"use client";

import { API_BASE_URL } from "@/services/api";
import { getStoredToken } from "@/lib/authStorage";

export interface RumMetricInput {
  metricName: string;
  route: string;
  sessionId: string;
  valueMs?: number | null;
  rating?: "good" | "needs-improvement" | "poor" | "info" | null;
  navigationType?: string | null;
  browserName?: string | null;
  osName?: string | null;
  deviceType?: string | null;
  language?: string | null;
  timezone?: string | null;
  screenWidth?: number | null;
  screenHeight?: number | null;
  metadata?: Record<string, unknown>;
}

export async function sendRumMetric(input: RumMetricInput): Promise<void> {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/ops/rum`, {
    method: "POST",
    keepalive: true,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      metric_name: input.metricName,
      route: input.route,
      session_id: input.sessionId,
      value_ms: input.valueMs ?? null,
      rating: input.rating ?? null,
      navigation_type: input.navigationType ?? null,
      browser_name: input.browserName ?? null,
      os_name: input.osName ?? null,
      device_type: input.deviceType ?? null,
      language: input.language ?? null,
      timezone: input.timezone ?? null,
      screen_width: input.screenWidth ?? null,
      screen_height: input.screenHeight ?? null,
      metadata: input.metadata ?? {},
    }),
  });

  if (!response.ok) {
    throw new Error(`RUM ingest failed with ${response.status}`);
  }
}

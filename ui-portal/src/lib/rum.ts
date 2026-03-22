"use client";

import { buildClientTelemetryProfile } from "@/lib/telemetry";
import type { RumMetricInput } from "@/services/rumService";

export interface NavigationEntryLike {
  type?: string;
  unloadEventEnd?: number;
  fetchStart?: number;
  domainLookupStart?: number;
  domainLookupEnd?: number;
  connectStart?: number;
  connectEnd?: number;
  secureConnectionStart?: number;
  requestStart?: number;
  responseStart?: number;
  responseEnd?: number;
  domInteractive?: number;
  domContentLoadedEventEnd?: number;
  loadEventEnd?: number;
}

function roundMetric(value: number | undefined): number | null {
  if (value === undefined || !Number.isFinite(value) || value < 0) {
    return null;
  }
  return Math.round(value * 100) / 100;
}

function buildBaseMetric(
  pathname: string,
  sessionId: string,
): Omit<RumMetricInput, "metricName"> {
  const profile = buildClientTelemetryProfile();
  return {
    route: pathname,
    sessionId,
    browserName: profile.browserName,
    osName: profile.osName,
    deviceType: profile.deviceType,
    language: profile.language,
    timezone: profile.timezone,
    screenWidth: profile.screenWidth,
    screenHeight: profile.screenHeight,
  };
}

export function buildNavigationRumMetrics(
  pathname: string,
  sessionId: string,
  navigationEntry: NavigationEntryLike | null | undefined,
): RumMetricInput[] {
  if (navigationEntry == null) {
    return [];
  }

  const baseMetric = buildBaseMetric(pathname, sessionId);
  const navigationType = navigationEntry.type ?? "navigate";
  const metrics: Array<[string, number | null]> = [
    ["page_load", roundMetric(navigationEntry.loadEventEnd)],
    ["dom_interactive", roundMetric(navigationEntry.domInteractive)],
    ["dom_content_loaded", roundMetric(navigationEntry.domContentLoadedEventEnd)],
    ["time_to_first_byte", roundMetric((navigationEntry.responseStart ?? 0) - (navigationEntry.requestStart ?? 0))],
    ["dns_lookup", roundMetric((navigationEntry.domainLookupEnd ?? 0) - (navigationEntry.domainLookupStart ?? 0))],
    ["tcp_connect", roundMetric((navigationEntry.connectEnd ?? 0) - (navigationEntry.connectStart ?? 0))],
    [
      "tls_handshake",
      navigationEntry.secureConnectionStart && navigationEntry.connectEnd
        ? roundMetric(navigationEntry.connectEnd - navigationEntry.secureConnectionStart)
        : null,
    ],
    ["request_response", roundMetric((navigationEntry.responseEnd ?? 0) - (navigationEntry.requestStart ?? 0))],
  ];

  return metrics
    .filter(([, valueMs]) => valueMs !== null)
    .map(([metricName, valueMs]) => ({
      ...baseMetric,
      metricName,
      navigationType,
      valueMs,
      rating: "info",
      metadata: {
        metric_source: "navigation",
      },
    }));
}

export function buildPaintMetric(
  pathname: string,
  sessionId: string,
  metricName: string,
  valueMs: number,
): RumMetricInput {
  return {
    ...buildBaseMetric(pathname, sessionId),
    metricName,
    valueMs: roundMetric(valueMs),
    rating: "info",
    metadata: {
      metric_source: "paint",
    },
  };
}

export function buildRouteTransitionMetric(
  pathname: string,
  sessionId: string,
  valueMs: number,
): RumMetricInput {
  return {
    ...buildBaseMetric(pathname, sessionId),
    metricName: "route_transition",
    valueMs: roundMetric(valueMs),
    rating: "info",
    metadata: {
      metric_source: "nextjs-route",
    },
  };
}

export function buildLayoutShiftMetric(
  pathname: string,
  sessionId: string,
  score: number,
): RumMetricInput {
  return {
    ...buildBaseMetric(pathname, sessionId),
    metricName: "cumulative_layout_shift",
    valueMs: roundMetric(score * 1000),
    rating: score <= 0.1 ? "good" : score <= 0.25 ? "needs-improvement" : "poor",
    metadata: {
      cls_score: roundMetric(score),
      metric_source: "layout-shift",
    },
  };
}

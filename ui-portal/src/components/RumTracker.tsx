"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import {
  buildLayoutShiftMetric,
  buildNavigationRumMetrics,
  buildPaintMetric,
  buildRouteTransitionMetric,
} from "@/lib/rum";
import { getOrCreateTelemetrySessionId } from "@/lib/telemetry";
import { sendRumMetric } from "@/services/rumService";

type LayoutShiftEntry = PerformanceEntry & {
  hadRecentInput?: boolean;
  value?: number;
};

export default function RumTracker(): null {
  const pathname = usePathname();
  const didEmitNavigationMetricsRef = useRef<boolean>(false);
  const didObserveInitialVitalsRef = useRef<boolean>(false);

  useEffect(() => {
    if (!pathname || typeof window === "undefined") {
      return;
    }

    const sessionId = getOrCreateTelemetrySessionId();
    const routeStart = window.performance.now();
    const send = (promise: Promise<void>): void => {
      void promise.catch(() => undefined);
    };

    if (!didEmitNavigationMetricsRef.current) {
      didEmitNavigationMetricsRef.current = true;
      const navigationEntry = window.performance.getEntriesByType("navigation")[0] as
        | PerformanceNavigationTiming
        | undefined;
      for (const metric of buildNavigationRumMetrics(pathname, sessionId, navigationEntry)) {
        send(sendRumMetric(metric));
      }
    }

    const paintObserver =
      !didObserveInitialVitalsRef.current && typeof PerformanceObserver !== "undefined"
        ? new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
              if (entry.entryType !== "paint") {
                continue;
              }
              send(sendRumMetric(buildPaintMetric(pathname, sessionId, entry.name, entry.startTime)));
            }
          })
        : null;

    const layoutShiftObserver =
      !didObserveInitialVitalsRef.current && typeof PerformanceObserver !== "undefined"
        ? new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries() as LayoutShiftEntry[]) {
              if (entry.hadRecentInput) {
                continue;
              }
              if (typeof entry.value === "number") {
                send(sendRumMetric(buildLayoutShiftMetric(pathname, sessionId, entry.value)));
              }
            }
          })
        : null;

    if (!didObserveInitialVitalsRef.current) {
      didObserveInitialVitalsRef.current = true;
      try {
        paintObserver?.observe({ type: "paint", buffered: true });
      } catch {
        paintObserver?.disconnect();
      }
      try {
        layoutShiftObserver?.observe({ type: "layout-shift", buffered: true });
      } catch {
        layoutShiftObserver?.disconnect();
      }
    }

    let secondFrame = 0;
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        send(sendRumMetric(buildRouteTransitionMetric(pathname, sessionId, window.performance.now() - routeStart)));
      });
    });

    return () => {
      window.cancelAnimationFrame(firstFrame);
      if (secondFrame !== 0) {
        window.cancelAnimationFrame(secondFrame);
      }
      paintObserver?.disconnect();
      layoutShiftObserver?.disconnect();
    };
  }, [pathname]);

  return null;
}

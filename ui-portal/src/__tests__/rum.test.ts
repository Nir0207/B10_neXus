import {
  buildLayoutShiftMetric,
  buildNavigationRumMetrics,
  buildRouteTransitionMetric,
} from "@/lib/rum";

describe("RUM helpers", () => {
  it("builds navigation metrics from navigation timing data", () => {
    const metrics = buildNavigationRumMetrics("/explorer", "session-1", {
      type: "navigate",
      requestStart: 50,
      responseStart: 120,
      responseEnd: 200,
      domainLookupStart: 10,
      domainLookupEnd: 20,
      connectStart: 20,
      connectEnd: 40,
      secureConnectionStart: 25,
      domInteractive: 350,
      domContentLoadedEventEnd: 500,
      loadEventEnd: 900,
    });

    expect(metrics.map((metric) => metric.metricName)).toEqual(
      expect.arrayContaining(["page_load", "dom_interactive", "time_to_first_byte", "tls_handshake"]),
    );
    expect(metrics.every((metric) => metric.route === "/explorer")).toBe(true);
  });

  it("scores route transition and cls metrics", () => {
    const routeMetric = buildRouteTransitionMetric("/telemetry", "session-2", 123.456);
    const clsMetric = buildLayoutShiftMetric("/telemetry", "session-2", 0.28);

    expect(routeMetric.metricName).toBe("route_transition");
    expect(routeMetric.valueMs).toBe(123.46);
    expect(clsMetric.rating).toBe("poor");
    expect(clsMetric.metadata?.cls_score).toBe(0.28);
  });
});

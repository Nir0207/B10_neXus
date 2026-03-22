import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import TelemetryDashboard from "@/components/TelemetryDashboard";
import { useAuth } from "@/components/AuthProvider";
import { fetchTelemetryDashboard } from "@/services/telemetryService";
import { exportToPharmaHTML } from "@/utils/HtmlExporter";

jest.mock("@/components/AuthProvider", () => ({
  useAuth: jest.fn(),
}));

jest.mock("@/services/telemetryService", () => ({
  fetchTelemetryDashboard: jest.fn(),
}));

jest.mock("@/utils/HtmlExporter", () => ({
  exportToPharmaHTML: jest.fn().mockResolvedValue(undefined),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedFetchTelemetryDashboard = fetchTelemetryDashboard as jest.MockedFunction<
  typeof fetchTelemetryDashboard
>;
const mockedExportToPharmaHTML = exportToPharmaHTML as jest.MockedFunction<typeof exportToPharmaHTML>;

describe("TelemetryDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      isReady: true,
      isSubmitting: false,
      login: jest.fn(),
      logout: jest.fn(),
      register: jest.fn(),
      session: {
        token: "jwt-token",
        username: "admin",
        email: "admin@bionexus.dev",
        fullName: "BioNexus Admin",
        isAdmin: true,
        issuedAt: "2026-03-22T00:00:00.000Z",
      },
    });
  });

  it("renders comparative telemetry metrics from the GraphQL service", async () => {
    mockedFetchTelemetryDashboard.mockResolvedValue({
      generatedAt: "2026-03-22T10:00:00.000Z",
      rangeDays: 7,
      totalEvents: 24,
      uniqueUsers: 6,
      activeRoutes: 4,
      averageEventsPerUser: 4,
      dailyActivity: [
        {
          date: "2026-03-21",
          totalEvents: 12,
          uniqueUsers: 4,
          adminEvents: 3,
          nonAdminEvents: 9,
        },
      ],
      eventComparison: [
        { key: "page_view", count: 18 },
        { key: "click", count: 6 },
      ],
      routeComparison: [{ key: "/explorer", count: 10 }],
      browserComparison: [{ key: "Chrome", count: 12 }],
      deviceComparison: [{ key: "desktop", count: 20 }],
      userSegmentComparison: [
        { key: "Admin", count: 5 },
        { key: "Non-Admin", count: 19 },
      ],
      recentEvents: [
        {
          id: "1",
          username: "admin",
          isAdmin: true,
          eventType: "page_view",
          route: "/telemetry",
          label: "/telemetry",
          browserName: "Chrome",
          deviceType: "desktop",
          createdAt: "2026-03-22T09:50:00.000Z",
        },
      ],
    });

    render(<TelemetryDashboard />);

    await waitFor(() => {
      expect(mockedFetchTelemetryDashboard).toHaveBeenCalledWith(7, "jwt-token");
    });

    expect(await screen.findByText(/comparative portal telemetry/i)).toBeInTheDocument();
    expect(await screen.findByText("24")).toBeInTheDocument();
    expect(await screen.findByText("6")).toBeInTheDocument();
    expect(screen.getByText("Export the telemetry snapshot as standalone HTML")).toBeInTheDocument();
    expect(screen.getByText("Latest authenticated client signals")).toBeInTheDocument();
    expect(screen.getAllByText("/telemetry").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /export report/i }));

    expect(mockedExportToPharmaHTML).toHaveBeenCalledWith(
      expect.objectContaining({
        chart_type: "line",
        disease_id: "telemetry-7-days",
        disease_name: "Portal Telemetry",
        report_id: "BNX-TELEMETRY-7D",
        model_name: "BioNexus Telemetry Engine",
        title: "Telemetry Activity - Last 7 Days",
      }),
    );
  });
});

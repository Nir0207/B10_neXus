import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react";
import TelemetryTracker from "@/components/TelemetryTracker";
import { useAuth } from "@/components/AuthProvider";
import { recordTelemetryEvent } from "@/services/telemetryService";

jest.mock("next/navigation", () => ({
  usePathname: () => "/explorer",
}));

jest.mock("@/components/AuthProvider", () => ({
  useAuth: jest.fn(),
}));

jest.mock("@/services/telemetryService", () => ({
  recordTelemetryEvent: jest.fn().mockResolvedValue(undefined),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedRecordTelemetryEvent = recordTelemetryEvent as jest.MockedFunction<
  typeof recordTelemetryEvent
>;

describe("TelemetryTracker", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
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

  it("captures page views and click events for authenticated sessions", async () => {
    const { getByRole } = render(
      <>
        <TelemetryTracker />
        <button data-telemetry-label="Launch Atlas" type="button">
          Launch Atlas
        </button>
      </>,
    );

    await waitFor(() => {
      expect(mockedRecordTelemetryEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: "page_view",
          route: "/explorer",
          sessionId: expect.any(String),
        }),
        "jwt-token",
      );
    });

    fireEvent.click(getByRole("button", { name: /launch atlas/i }));

    await waitFor(() => {
      expect(mockedRecordTelemetryEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: "click",
          route: "/explorer",
          label: "Launch Atlas",
        }),
        "jwt-token",
      );
    });
  });
});

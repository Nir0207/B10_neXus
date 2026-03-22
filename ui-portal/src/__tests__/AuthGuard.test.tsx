import React from "react";
import { render, screen } from "@testing-library/react";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/components/AuthProvider";

const replaceMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/telemetry",
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

jest.mock("@/components/AuthProvider", () => ({
  useAuth: jest.fn(),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe("AuthGuard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("blocks admin-only routes for non-admin users", () => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      isReady: true,
      isSubmitting: false,
      login: jest.fn(),
      logout: jest.fn(),
      register: jest.fn(),
      session: {
        token: "jwt-token",
        username: "scientist.one",
        email: "scientist.one@bionexus.dev",
        fullName: "Scientist One",
        isAdmin: false,
        issuedAt: "2026-03-22T00:00:00.000Z",
      },
    });

    render(
      <AuthGuard requireAdmin>
        <div>Secret telemetry</div>
      </AuthGuard>,
    );

    expect(screen.getByText(/admin access required/i)).toBeInTheDocument();
    expect(screen.queryByText("Secret telemetry")).not.toBeInTheDocument();
  });
});

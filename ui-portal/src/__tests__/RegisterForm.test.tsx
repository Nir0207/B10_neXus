import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import RegisterForm from "@/components/RegisterForm";
import { useAuth } from "@/components/AuthProvider";

const replaceMock = jest.fn();
const registerMock = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

jest.mock("@/components/AuthProvider", () => ({
  useAuth: jest.fn(),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe("RegisterForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      isAuthenticated: false,
      isReady: true,
      isSubmitting: false,
      login: jest.fn(),
      logout: jest.fn(),
      register: registerMock,
      session: null,
    });
  });

  it("submits registration details and redirects to the next route", async () => {
    registerMock.mockResolvedValue(undefined);

    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: "Scientist One" } });
    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "scientist.one" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "scientist.one@bionexus.dev" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "strongpassword" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "strongpassword" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith({
        fullName: "Scientist One",
        username: "scientist.one",
        email: "scientist.one@bionexus.dev",
        password: "strongpassword",
      });
    });
    expect(replaceMock).toHaveBeenCalledWith("/explorer");
  });

  it("blocks submission when the passwords do not match", async () => {
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "scientist.one" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "scientist.one@bionexus.dev" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "strongpassword" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "wrongpassword" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(registerMock).not.toHaveBeenCalled();
  });
});

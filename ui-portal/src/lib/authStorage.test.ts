import {
  buildBootstrapSession,
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
} from "@/lib/authStorage";

describe("authStorage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    process.env.NEXT_PUBLIC_BIONEXUS_API_TOKEN = "bootstrap-token";
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_BIONEXUS_API_TOKEN;
  });

  it("persists and restores an auth session", () => {
    saveAuthSession({
      token: "jwt-token",
      username: "auditor",
      issuedAt: "2026-03-21T10:00:00.000Z",
    });

    expect(loadAuthSession()).toEqual({
      token: "jwt-token",
      username: "auditor",
      issuedAt: "2026-03-21T10:00:00.000Z",
    });
  });

  it("allows one-time bootstrap from the environment until logout", () => {
    expect(buildBootstrapSession()?.token).toBe("bootstrap-token");

    clearAuthSession();

    expect(buildBootstrapSession()).toBeNull();
  });
});

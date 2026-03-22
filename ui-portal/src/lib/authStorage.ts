"use client";

export interface AuthSession {
  token: string;
  username: string;
  email: string | null;
  fullName: string | null;
  isAdmin: boolean;
  issuedAt: string;
}

const AUTH_SESSION_KEY = "bionexus.auth.session";
const AUTH_ENV_DISMISSED_KEY = "bionexus.auth.dismissedEnvToken";
const ENV_BOOTSTRAP_USERNAME = "BioNexus Operator";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function loadAuthSession(): AuthSession | null {
  if (!canUseStorage()) {
    return null;
  }

  const rawValue = window.localStorage.getItem(AUTH_SESSION_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<AuthSession>;
    if (
      typeof parsed.token !== "string" ||
      typeof parsed.username !== "string" ||
      typeof parsed.issuedAt !== "string" ||
      typeof parsed.isAdmin !== "boolean"
    ) {
      window.localStorage.removeItem(AUTH_SESSION_KEY);
      return null;
    }

    return {
      token: parsed.token,
      username: parsed.username,
      email: typeof parsed.email === "string" ? parsed.email : null,
      fullName: typeof parsed.fullName === "string" ? parsed.fullName : null,
      isAdmin: parsed.isAdmin,
      issuedAt: parsed.issuedAt,
    };
  } catch {
    window.localStorage.removeItem(AUTH_SESSION_KEY);
    return null;
  }
}

export function saveAuthSession(session: AuthSession): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  window.localStorage.removeItem(AUTH_ENV_DISMISSED_KEY);
}

export function clearAuthSession(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(AUTH_SESSION_KEY);
  window.localStorage.setItem(AUTH_ENV_DISMISSED_KEY, "1");
}

export function buildBootstrapSession(): AuthSession | null {
  const bootstrapToken = process.env.NEXT_PUBLIC_BIONEXUS_API_TOKEN?.trim();
  if (!bootstrapToken || !canUseStorage()) {
    return null;
  }

  if (window.localStorage.getItem(AUTH_ENV_DISMISSED_KEY) === "1") {
    return null;
  }

  return {
    token: bootstrapToken,
    username: ENV_BOOTSTRAP_USERNAME,
    email: null,
    fullName: ENV_BOOTSTRAP_USERNAME,
    isAdmin: false,
    issuedAt: new Date().toISOString(),
  };
}

export function getStoredToken(): string | null {
  return loadAuthSession()?.token ?? buildBootstrapSession()?.token ?? null;
}

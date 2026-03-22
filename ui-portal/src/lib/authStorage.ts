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
  // Do not restore authentication tokens or sessions from localStorage.
  // Tokens are kept in memory only to avoid clear text storage of sensitive data.
  return null;
}

export function saveAuthSession(session: AuthSession): void {
  // Intentionally do not persist the AuthSession (and especially the token)
  // to localStorage to avoid clear text storage of sensitive authentication data.
  if (!canUseStorage()) {
    return;
  }

  // Previously, the full session including the token was stored under AUTH_SESSION_KEY.
  // This has been disabled for security reasons.
  window.localStorage.removeItem(AUTH_ENV_DISMISSED_KEY);
}

export function clearAuthSession(): void {
  if (!canUseStorage()) {
    return;
  }

  // Ensure any legacy stored session is removed and record that the env token
  // has been dismissed for this browser.
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
  // Since AuthSession is no longer persisted, only the bootstrap token
  // (derived from NEXT_PUBLIC_BIONEXUS_API_TOKEN) can be returned here.
  return buildBootstrapSession()?.token ?? null;
}

"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
} from "react";
import {
  buildBootstrapSession,
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
  type AuthSession,
} from "@/lib/authStorage";
import { loginWithPassword, registerWithPassword, type RegisterPayload } from "@/services/authService";
import { fetchCurrentUser } from "@/services/telemetryService";

interface LoginPayload {
  username: string;
  password: string;
}

interface AuthContextValue {
  isAuthenticated: boolean;
  isReady: boolean;
  isSubmitting: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  session: AuthSession | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren): React.JSX.Element {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isReady, setIsReady] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    async function restoreSession(): Promise<void> {
      // Do not attempt to restore an AuthSession (and token) from localStorage.
      // Only use a bootstrap session based on a public environment token, if available.
      const baseSession = buildBootstrapSession();
      if (!baseSession) {
        if (isMounted) {
          setIsReady(true);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(baseSession.token);
        const hydratedSession: AuthSession = {
          ...baseSession,
          username: user.username,
          email: user.email,
          fullName: user.fullName ?? null,
          isAdmin: user.isAdmin,
        };

        if (!isMounted) {
          return;
        }

        // Keep the hydrated session in memory only; do not persist it.
        setSession(hydratedSession);
      } catch {
        if (!isMounted) {
          return;
        }

        if (baseSession.token) {
          clearAuthSession();
          setSession(null);
        } else {
          setSession(baseSession);
        }
      } finally {
        if (isMounted) {
          setIsReady(true);
        }
      }
    }

    void restoreSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const value: AuthContextValue = {
    isAuthenticated: Boolean(session?.token),
    isReady,
    isSubmitting,
    login: async ({ username, password }: LoginPayload) => {
      setIsSubmitting(true);
      try {
        const nextSession = await loginWithPassword(username, password);
        // Do not persist the session to localStorage; keep it in memory only.
        setSession(nextSession);
      } finally {
        setIsSubmitting(false);
      }
    },
    register: async (payload: RegisterPayload) => {
      setIsSubmitting(true);
      try {
        const nextSession = await registerWithPassword(payload);
        // Do not persist the session to localStorage; keep it in memory only.
        setSession(nextSession);
      } finally {
        setIsSubmitting(false);
      }
    },
    logout: () => {
      clearAuthSession();
      setSession(null);
    },
    session,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}

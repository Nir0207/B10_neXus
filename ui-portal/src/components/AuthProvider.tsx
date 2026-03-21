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
    const storedSession = loadAuthSession();
    if (storedSession) {
      setSession(storedSession);
      setIsReady(true);
      return;
    }

    const bootstrapSession = buildBootstrapSession();
    if (bootstrapSession) {
      saveAuthSession(bootstrapSession);
      setSession(bootstrapSession);
    }

    setIsReady(true);
  }, []);

  const value: AuthContextValue = {
    isAuthenticated: Boolean(session?.token),
    isReady,
    isSubmitting,
    login: async ({ username, password }: LoginPayload) => {
      setIsSubmitting(true);
      try {
        const nextSession = await loginWithPassword(username, password);
        saveAuthSession(nextSession);
        setSession(nextSession);
      } finally {
        setIsSubmitting(false);
      }
    },
    register: async (payload: RegisterPayload) => {
      setIsSubmitting(true);
      try {
        const nextSession = await registerWithPassword(payload);
        saveAuthSession(nextSession);
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

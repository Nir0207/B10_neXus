"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

const DEFAULT_USERNAME = "admin";
const DEFAULT_PASSWORD = "password";
const DEFAULT_NEXT_PATH = "/explorer";

function resolveNextPath(): string {
  if (typeof window === "undefined") {
    return DEFAULT_NEXT_PATH;
  }

  const url = new URL(window.location.href);
  return url.searchParams.get("next") || DEFAULT_NEXT_PATH;
}

export default function LoginForm(): React.JSX.Element {
  const router = useRouter();
  const { isAuthenticated, isReady, isSubmitting, login } = useAuth();

  const [username, setUsername] = useState<string>(DEFAULT_USERNAME);
  const [password, setPassword] = useState<string>(DEFAULT_PASSWORD);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [nextPath] = useState<string>(resolveNextPath);

  useEffect(() => {
    if (isReady && isAuthenticated) {
      router.replace(nextPath);
    }
  }, [isAuthenticated, isReady, nextPath, router]);

  return (
    <div className="relative z-10 min-h-screen flex items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-6xl lg:grid-cols-[1.2fr_0.8fr] gap-10 items-center">
        <section className="space-y-8">
          <div className="space-y-5">
            <p className="text-xs uppercase tracking-[0.35em] text-primary">BioNexus Access</p>
            <h1 className="max-w-2xl text-5xl font-headline font-extrabold leading-tight text-on-surface">
              Local-first multi-omics review, graph discovery, and therapeutic traceability.
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-on-surface-variant">
              Sign in to inspect the live Gene-Disease-Medicine graph, review pathway evidence,
              and audit the current discovery flow against the running gateway.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Telemetry API", "GraphQL login and session enrichment on port 4100"],
              ["Graph", "Neo4j triplets scoped by organ through the existing gateway"],
              ["Audit", "Mongo-backed user roles and client telemetry capture"],
            ].map(([label, copy]) => (
              <div
                className="rounded-2xl border border-outline-variant/15 bg-surface-container-low/80 p-5 shadow-xl"
                key={label}
              >
                <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">{label}</p>
                <p className="text-sm text-on-surface-variant leading-relaxed">{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-outline-variant/20 bg-surface-container-low/95 p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3">Secure Login</p>
            <h2 className="text-3xl font-headline font-bold mb-3">Authenticate to BioNexus</h2>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Use the telemetry GraphQL credentials to mint a JWT and unlock the explorer routes.
            </p>
          </div>

          <form
            className="space-y-5"
            onSubmit={async (event) => {
              event.preventDefault();
              setErrorMessage("");

              try {
                await login({ username, password });
                router.replace(nextPath);
              } catch (error) {
                setErrorMessage(
                  error instanceof Error
                    ? error.message
                    : "Authentication failed. Verify the telemetry service credentials."
                );
              }
            }}
          >
            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Username
              </span>
              <input
                autoComplete="username"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                onChange={(event) => setUsername(event.target.value)}
                value={username}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Password
              </span>
              <input
                autoComplete="current-password"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>

            {errorMessage ? (
              <div className="rounded-2xl border border-error/40 bg-error-container/20 px-4 py-3 text-sm text-error">
                {errorMessage}
              </div>
            ) : null}

            <button
              className="w-full rounded-2xl bg-primary px-4 py-3 text-sm font-bold text-on-primary transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!isReady || isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Signing In..." : "Sign In"}
            </button>
          </form>

          <div className="mt-6 rounded-2xl border border-outline-variant/15 bg-background/60 p-4 text-xs text-on-surface-variant">
            <p className="uppercase tracking-[0.24em] text-primary mb-2">Default Dev Credentials</p>
            <p>`admin` / `password`</p>
          </div>

          <div className="mt-5 text-center text-sm text-on-surface-variant">
            Need an account?{" "}
            <Link className="font-semibold text-primary hover:opacity-80" href="/register">
              Create one
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}

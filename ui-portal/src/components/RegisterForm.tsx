"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

const DEFAULT_NEXT_PATH = "/explorer";

function resolveNextPath(): string {
  if (typeof window === "undefined") {
    return DEFAULT_NEXT_PATH;
  }

  const url = new URL(window.location.href);
  return url.searchParams.get("next") || DEFAULT_NEXT_PATH;
}

export default function RegisterForm(): React.JSX.Element {
  const router = useRouter();
  const { isAuthenticated, isReady, isSubmitting, register } = useAuth();

  const [fullName, setFullName] = useState<string>("");
  const [username, setUsername] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [nextPath] = useState<string>(resolveNextPath);

  useEffect(() => {
    if (isReady && isAuthenticated) {
      router.replace(nextPath);
    }
  }, [isAuthenticated, isReady, nextPath, router]);

  return (
    <div className="relative z-10 min-h-screen flex items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-6xl lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
        <section className="space-y-8">
          <div className="space-y-5">
            <p className="text-xs uppercase tracking-[0.35em] text-primary">BioNexus Registration</p>
            <h1 className="max-w-2xl text-5xl font-headline font-extrabold leading-tight text-on-surface">
              Provision a workspace identity for graph exploration and evidence review.
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-on-surface-variant">
              Create a user backed by the gateway database, receive a live JWT, and move
              directly into the explorer without relying on the shared dev admin account.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Users", "Persisted in Postgres with PBKDF2 password hashes"],
              ["Access", "JWT issued immediately after successful registration"],
              ["Traceability", "Individual usernames appear in the UI session state"],
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
            <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3">Create Account</p>
            <h2 className="text-3xl font-headline font-bold mb-3">Register for BioNexus</h2>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Choose a unique username, attach an email, and create a password with at least
              eight characters.
            </p>
          </div>

          <form
            className="space-y-5"
            onSubmit={async (event) => {
              event.preventDefault();
              setErrorMessage("");

              if (password !== confirmPassword) {
                setErrorMessage("Passwords do not match.");
                return;
              }

              try {
                await register({
                  fullName,
                  username,
                  email,
                  password,
                });
                router.replace(nextPath);
              } catch (error) {
                setErrorMessage(
                  error instanceof Error
                    ? error.message
                    : "Registration failed. Verify the details and try again."
                );
              }
            }}
          >
            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Full Name
              </span>
              <input
                autoComplete="name"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Research lead"
                value={fullName}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Username
              </span>
              <input
                autoComplete="username"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                onChange={(event) => setUsername(event.target.value)}
                placeholder="bio.operator"
                required
                value={username}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Email
              </span>
              <input
                autoComplete="email"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="operator@bionexus.dev"
                required
                type="email"
                value={email}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Password
              </span>
              <input
                autoComplete="new-password"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Confirm Password
              </span>
              <input
                autoComplete="new-password"
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-high px-4 py-3 text-sm outline-none transition-colors focus:border-primary/50"
                minLength={8}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                type="password"
                value={confirmPassword}
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
              {isSubmitting ? "Creating Account..." : "Create Account"}
            </button>
          </form>

          <div className="mt-5 text-center text-sm text-on-surface-variant">
            Already have an account?{" "}
            <Link className="font-semibold text-primary hover:opacity-80" href="/login">
              Sign in
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}

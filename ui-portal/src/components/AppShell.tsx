"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

interface NavigationItem {
  href: string;
  label: string;
  requiresAdmin?: boolean;
}

const PRIMARY_NAV: readonly NavigationItem[] = [
  { href: "/explorer", label: "Explorer" },
  { href: "/pathways", label: "Pathways" },
  { href: "/clinical-trials", label: "Clinical Trials" },
  { href: "/historical-trends", label: "Historical Trends" },
  { href: "/telemetry", label: "Telemetry", requiresAdmin: true },
];

function isActivePath(currentPathname: string, href: string): boolean {
  if (href === "/explorer") {
    return currentPathname === "/" || currentPathname.startsWith("/explorer");
  }

  return currentPathname.startsWith(href);
}

export default function AppShell({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isReady, logout, session } = useAuth();

  if (pathname === "/login" || pathname === "/register") {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-[-10%] right-[-8%] w-[52rem] h-[52rem] rounded-full bg-primary/10 blur-[120px]" />
          <div className="absolute bottom-[-25%] left-[-12%] w-[42rem] h-[42rem] rounded-full bg-tertiary/10 blur-[110px]" />
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="text-on-surface overflow-hidden h-screen flex flex-col bg-background">
      <header className="flex justify-between items-center w-full px-6 h-14 z-50 bg-background/95 backdrop-blur-md border-b border-outline-variant/10">
        <div className="flex items-center gap-8">
          <Link
            className="text-xl font-bold tracking-tighter text-primary font-headline"
            data-testid="brand-primary"
            href="/explorer"
          >
            Genomic Portal
          </Link>
          <nav className="hidden md:flex items-center gap-6">
            {PRIMARY_NAV.filter((item) => !item.requiresAdmin || session?.isAdmin).map((item) => {
              const active = isActivePath(pathname, item.href);
              return (
                <Link
                  className={
                    active
                      ? "text-primary border-b-2 border-primary pb-1 text-sm font-medium transition-colors duration-150"
                      : "text-on-surface-variant hover:text-primary text-sm font-medium transition-colors duration-150"
                  }
                  href={item.href}
                  key={item.href}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-2 rounded-full border border-outline-variant/20 bg-surface-container-low px-3 py-1">
            <span className="material-symbols-outlined text-sm text-primary">verified_user</span>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-[0.25em] text-on-surface-variant">
                Session
              </span>
              <span className="text-xs font-semibold text-on-surface">
                {isReady && isAuthenticated ? session?.username ?? "Scientist" : "Guest"}
              </span>
              {session?.isAdmin ? (
                <span className="text-[10px] uppercase tracking-[0.24em] text-primary">
                  Admin
                </span>
              ) : null}
            </div>
          </div>

          <Link
            className="text-on-surface-variant hover:text-primary text-xs font-medium transition-colors"
            href="/documentation"
          >
            Documentation
          </Link>
          <Link
            className="text-on-surface-variant hover:text-primary text-xs font-medium transition-colors"
            href="/support"
          >
            Support
          </Link>

          {isAuthenticated ? (
            <button
              className="rounded-full border border-outline-variant/20 bg-surface-container-low px-3 py-1.5 text-xs font-semibold hover:border-primary/40 hover:text-primary transition-colors"
              onClick={() => {
                logout();
                router.push("/login");
              }}
              type="button"
            >
              Logout
            </button>
          ) : (
            <Link
              className="rounded-full border border-outline-variant/20 bg-surface-container-low px-3 py-1.5 text-xs font-semibold hover:border-primary/40 hover:text-primary transition-colors"
              href="/login"
            >
              Login
            </Link>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">{children}</div>
    </div>
  );
}

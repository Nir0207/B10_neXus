"use client";

import { useEffect, type PropsWithChildren } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

interface AuthGuardProps extends PropsWithChildren {
  requireAdmin?: boolean;
}

function AccessState({
  message,
}: {
  message: string;
}): React.JSX.Element {
  return (
    <div className="flex-1 flex items-center justify-center p-10">
      <div className="max-w-md rounded-2xl border border-outline-variant/20 bg-surface-container-low p-8 text-center shadow-2xl">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">Access Control</p>
        <h1 className="text-2xl font-headline font-bold mb-3">BioNexus UI Portal</h1>
        <p className="text-sm text-on-surface-variant leading-relaxed">{message}</p>
      </div>
    </div>
  );
}

export default function AuthGuard({
  children,
  requireAdmin = false,
}: AuthGuardProps): React.JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isReady, session } = useAuth();

  useEffect(() => {
    if (!isReady || isAuthenticated) {
      return;
    }

    router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [isAuthenticated, isReady, pathname, router]);

  if (!isReady) {
    return <AccessState message="Restoring your local BioNexus session." />;
  }

  if (!isAuthenticated) {
    return <AccessState message="Authentication required. Redirecting to the secure sign-in route." />;
  }

  if (requireAdmin && !session?.isAdmin) {
    return <AccessState message="Admin access required. This telemetry route is hidden for non-admin users." />;
  }

  return <>{children}</>;
}

"use client";

import { AuthProvider } from "@/components/AuthProvider";
import TelemetryTracker from "@/components/TelemetryTracker";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <TelemetryTracker />
      {children}
    </AuthProvider>
  );
}

"use client";

import { AuthProvider } from "@/components/AuthProvider";
import RumTracker from "@/components/RumTracker";
import TelemetryTracker from "@/components/TelemetryTracker";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <RumTracker />
      <TelemetryTracker />
      {children}
    </AuthProvider>
  );
}

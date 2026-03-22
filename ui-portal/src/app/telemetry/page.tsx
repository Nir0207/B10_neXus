import AuthGuard from "@/components/AuthGuard";
import TelemetryDashboard from "@/components/TelemetryDashboard";

export default function TelemetryPage(): React.JSX.Element {
  return (
    <AuthGuard requireAdmin>
      <TelemetryDashboard />
    </AuthGuard>
  );
}

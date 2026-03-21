import AuthGuard from "@/components/AuthGuard";
import DashboardView from "@/components/DashboardView";

export default function ExplorerPage(): React.JSX.Element {
  return (
    <AuthGuard>
      <DashboardView />
    </AuthGuard>
  );
}

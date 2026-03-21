import AuthGuard from "@/components/AuthGuard";
import PathwaysWorkbench from "@/components/PathwaysWorkbench";

export default function PathwaysPage(): React.JSX.Element {
  return (
    <AuthGuard>
      <PathwaysWorkbench />
    </AuthGuard>
  );
}

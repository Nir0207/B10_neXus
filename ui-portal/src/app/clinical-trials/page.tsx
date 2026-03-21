import AuthGuard from "@/components/AuthGuard";
import ClinicalTrialsBoard from "@/components/ClinicalTrialsBoard";

export default function ClinicalTrialsPage(): React.JSX.Element {
  return (
    <AuthGuard>
      <ClinicalTrialsBoard />
    </AuthGuard>
  );
}

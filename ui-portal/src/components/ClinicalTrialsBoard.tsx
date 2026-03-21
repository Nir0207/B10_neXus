"use client";

import { useMemo, useState } from "react";
import BioChat from "@/components/BioChat";
import OrganNavigator from "@/components/OrganNavigator";
import { findNode, scopeTripletsToOrgan, summarizeTriplets } from "@/lib/discovery";
import { useBioData } from "@/hooks/useBioData";

interface TrialRow {
  disease: string;
  medicine: string;
  gene: string;
  rationale: string;
}

export default function ClinicalTrialsBoard(): React.JSX.Element {
  const [organType, setOrganType] = useState<string>("liver");
  const { data, isLoading, isFetching, isError, error, refetch } = useBioData(organType);
  const scopedData = scopeTripletsToOrgan(data, organType);
  const summary = summarizeTriplets(scopedData);

  const trialRows = useMemo<TrialRow[]>(() => {
    return summary.diseaseMedicineEdges.map((edge) => {
      const disease = findNode(summary.diseases, edge.target);
      const medicine = findNode(summary.medicines, edge.source);
      const bindingEdge = summary.medicineGeneEdges.find(
        (candidate) => candidate.source === edge.source
      );
      const gene = bindingEdge ? findNode(summary.genes, bindingEdge.target) : undefined;
      return {
        disease: disease?.label ?? edge.target,
        medicine: medicine?.label ?? edge.source,
        gene: gene?.label ?? "Unresolved target",
        rationale: bindingEdge
          ? `${medicine?.label ?? edge.source} binds ${gene?.label ?? bindingEdge.target}`
          : "Awaiting direct medicine-gene binding evidence",
      };
    });
  }, [summary.diseaseMedicineEdges, summary.diseases, summary.genes, summary.medicineGeneEdges, summary.medicines]);

  const gatewayError =
    error instanceof Error
      ? error.message
      : "Clinical evidence is unavailable. Verify the API gateway and Neo4j graph.";

  return (
    <>
      <OrganNavigator
        onExport={() => {
          const payload = JSON.stringify(
            {
              organ: organType,
              trialRows,
            },
            null,
            2
          );
          const blob = new Blob([payload], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `bionexus-${organType}-clinical-board.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        }}
        selectedOrgan={organType}
        onSelectOrgan={setOrganType}
      />

      <main className="flex-1 overflow-y-auto bg-surface">
        <section className="px-8 py-7 border-b border-outline-variant/10">
          <p className="text-xs uppercase tracking-[0.28em] text-primary mb-3">Clinical Translation</p>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div className="max-w-3xl">
              <h1 className="text-3xl font-headline font-bold mb-3">
                Gene-Disease-Medicine candidates for the {organType} program
              </h1>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                This board projects the current triplet graph into a trial-planning view, highlighting
                disease burden, therapeutic candidates, and gene binding context.
              </p>
            </div>
            <button
              className="rounded-full border border-outline-variant/20 bg-surface-container-low px-4 py-2 text-xs font-semibold hover:border-primary/40 hover:text-primary transition-colors"
              onClick={() => {
                void refetch();
              }}
              type="button"
            >
              {isFetching ? "Refreshing..." : "Refresh Board"}
            </button>
          </div>
        </section>

        {isError ? (
          <div className="m-8 rounded-3xl border border-error/40 bg-error-container/20 p-6 text-sm text-error">
            {gatewayError}
          </div>
        ) : null}

        <section className="grid gap-6 px-8 py-8 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="space-y-6">
            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Program Snapshot</p>
              <div className="grid gap-3">
                {[
                  ["Trial-ready chains", String(trialRows.length)],
                  ["Unique diseases", String(summary.diseases.length)],
                  ["Therapeutic assets", String(summary.medicines.length)],
                ].map(([label, value]) => (
                  <div
                    className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4"
                    key={label}
                  >
                    <p className="text-[10px] uppercase tracking-[0.24em] text-on-surface-variant mb-2">
                      {label}
                    </p>
                    <p className="text-2xl font-headline font-bold">{value}</p>
                  </div>
                ))}
              </div>
            </article>

            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Operational Notes</p>
              <ul className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
                <li>UniProt remains the canonical cross-database key for gene resolution.</li>
                <li>Diseases are filtered by selected organ at the gateway query boundary.</li>
                <li>Logout clears the local session and forces re-authentication.</li>
              </ul>
            </article>
          </div>

          <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-2">Candidate Matrix</p>
                <h2 className="text-2xl font-headline font-bold">Graph-backed therapeutic rows</h2>
              </div>
              {isLoading ? (
                <span className="text-xs uppercase tracking-[0.22em] text-on-surface-variant">Loading</span>
              ) : null}
            </div>

            {trialRows.length === 0 ? (
              <div className="rounded-2xl border border-outline-variant/15 bg-background/60 p-6 text-sm text-on-surface-variant">
                No clinical candidate rows are available for this organ slice yet.
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-outline-variant/15">
                <div className="grid grid-cols-[1fr_1fr_1fr_1.4fr] bg-background/70 px-4 py-3 text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
                  <span>Disease</span>
                  <span>Medicine</span>
                  <span>Gene</span>
                  <span>Rationale</span>
                </div>
                <div className="divide-y divide-outline-variant/10">
                  {trialRows.map((row) => (
                    <div
                      className="grid grid-cols-[1fr_1fr_1fr_1.4fr] gap-4 bg-surface-container-lowest px-4 py-4 text-sm"
                      key={`${row.disease}-${row.medicine}-${row.gene}`}
                    >
                      <span>{row.disease}</span>
                      <span>{row.medicine}</span>
                      <span>{row.gene}</span>
                      <span className="text-on-surface-variant">{row.rationale}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </article>
        </section>
      </main>

      <BioChat data={scopedData} organType={organType} />
    </>
  );
}

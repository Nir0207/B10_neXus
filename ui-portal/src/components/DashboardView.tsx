"use client";

import { useState } from "react";
import BioChat from "@/components/BioChat";
import DiscoveryGraph from "@/components/DiscoveryGraph";
import GenomicMap from "@/components/GenomicMap";
import OrganNavigator from "@/components/OrganNavigator";
import { scopeTripletsToOrgan, summarizeTriplets } from "@/lib/discovery";
import { type ExplorerView, getOrganOption } from "@/lib/organs";
import { useBioData } from "@/hooks/useBioData";

const SEQUENCE_MARKERS = Array.from({ length: 28 }, (_, index) => ["A", "T", "G", "C"][index % 4]);

export default function DashboardView(): React.JSX.Element {
  const [organType, setOrganType] = useState<string>("liver");
  const [explorerView, setExplorerView] = useState<ExplorerView>("genomic-map");
  const { data, isLoading, isFetching, isError, error, refetch } = useBioData(organType);

  const isInitialLoad = isLoading && !data;
  const organ = getOrganOption(organType);
  const scopedData = scopeTripletsToOrgan(data, organType);
  const summary = summarizeTriplets(scopedData);
  const errorMessage =
    error instanceof Error
      ? error.message
      : "Failed to load biology data. Verify the API Gateway on port 8000.";

  return (
    <>
      <OrganNavigator
        onExport={() => {
          const payload = JSON.stringify(
            {
              organ: organType,
              explorerView,
              exportedAt: new Date().toISOString(),
              data,
            },
            null,
            2
          );
          const blob = new Blob([payload], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `bionexus-${organType}-triplets.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        }}
        onSelectExplorerView={setExplorerView}
        selectedOrgan={organType}
        selectedExplorerView={explorerView}
        onSelectOrgan={(nextOrgan) => {
          if (nextOrgan === organType) {
            void refetch();
            return;
          }

          setOrganType(nextOrgan);
        }}
      />

      <main className="flex-1 relative flex flex-col bg-surface overflow-hidden" data-testid="dashboard-root">
        <section className="px-8 py-6 border-b border-outline-variant/10">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-2">Explorer Workspace</p>
              <h1 className="text-3xl font-headline font-bold mb-2">
                {organ.label} {explorerView === "genomic-map" ? "genomic locus" : "discovery network"}
              </h1>
              <p className="text-sm text-on-surface-variant">
                Focus: {organ.focus}. Active target: {summary.genes[0]?.label ?? organ.primaryTarget}.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["Genes", String(summary.genes.length)],
                ["Diseases", String(summary.diseases.length)],
                ["Medicines", String(summary.medicines.length)],
              ].map(([label, value]) => (
                <div
                  className="rounded-2xl border border-outline-variant/15 bg-surface-container-low px-4 py-3 min-w-28"
                  key={label}
                >
                  <p className="text-[10px] uppercase tracking-[0.24em] text-on-surface-variant mb-2">
                    {label}
                  </p>
                  <p className="text-xl font-headline font-bold">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {explorerView === "genomic-map" ? (
          <>
            <div className="flex-1 flex items-center justify-center p-8 border-b border-outline-variant/10">
              <GenomicMap
                data={scopedData}
                isError={isError}
                isLoading={isInitialLoad}
                selectedOrgan={organType}
              />
            </div>

            <div className="h-24 bg-surface-container-lowest border-t border-outline-variant/10 px-8 flex flex-col justify-center shrink-0">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Genomic Sequence Scrubber ({organ.primaryTarget})
                </span>
                <span className="text-[10px] font-mono text-primary">
                  Focus risk: {organ.keyRisk}
                </span>
              </div>
              <div className="h-6 w-full bg-surface-container-highest rounded-sm relative overflow-hidden flex items-center px-1">
                <div className="absolute left-1/4 w-1/3 h-full bg-primary/20 border-x border-primary" />
                <div className="flex gap-1 w-full opacity-60">
                  {SEQUENCE_MARKERS.map((marker, index) => (
                    <span
                      className="text-[9px] font-mono w-4 text-center"
                      key={`${marker}-${index}`}
                    >
                      {marker}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 min-h-0 bg-surface-container-lowest">
            <DiscoveryGraph
              data={scopedData}
              errorMessage={errorMessage}
              isError={isError}
              isLoading={isInitialLoad}
              isRefreshing={isFetching && Boolean(data)}
              onRetry={() => {
                void refetch();
              }}
              selectedOrgan={organType}
            />
          </div>
        )}
      </main>

      <BioChat data={scopedData} organType={organType} />

      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        <div className="absolute top-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-primary/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-tertiary/5 blur-[100px]" />
      </div>
    </>
  );
}

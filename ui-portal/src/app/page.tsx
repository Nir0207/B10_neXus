"use client";

import { useState } from "react";
import OrganNavigator from "@/components/OrganNavigator";
import GenomicMap from "@/components/GenomicMap";
import DiscoveryGraph from "@/components/DiscoveryGraph";
import BioChat from "@/components/BioChat";
import { useBioNexus } from "../../hooks/useBioNexus";

const SEQUENCE_MARKERS = Array.from({ length: 28 }, (_, index) => ["A", "T", "G", "C"][index % 4]);

export default function Dashboard() {
  const [organType, setOrganType] = useState("liver");
  const { data, isLoading, isFetching, isError, error, refetch } = useBioNexus(organType);

  const isInitialLoad = isLoading && !data;
  const errorMessage =
    error instanceof Error
      ? error.message
      : "Failed to load biology data. Verify the API Gateway on port 8000.";

  const handleSelectOrgan = (nextOrgan: string) => {
    if (nextOrgan === organType) {
      void refetch();
      return;
    }

    setOrganType(nextOrgan);
  };

  return (
    <>
      <OrganNavigator selectedOrgan={organType} onSelectOrgan={handleSelectOrgan} />

      <main className="flex-1 relative flex flex-col bg-surface overflow-hidden" data-testid="dashboard-root">
        {/* Top half: Genomic Map Layer */}
        <div className="flex-1 flex items-center justify-center p-8 border-b border-outline-variant/10">
          <GenomicMap isError={isError} isLoading={isInitialLoad} selectedOrgan={organType} />
        </div>

        {/* Bottom half: Network Graph Layer */}
        <div className="h-2/5 min-h-[300px] flex flex-col bg-surface-container-lowest relative">
          <DiscoveryGraph
            data={data}
            errorMessage={errorMessage}
            isError={isError}
            isLoading={isInitialLoad}
            isRefreshing={isFetching && Boolean(data)}
            onRetry={() => {
              void refetch();
            }}
          />

          {/* Sequence Scrubber (from mock) */}
          <div className="h-20 bg-surface-container-lowest border-t border-outline-variant/10 px-8 flex flex-col justify-center shrink-0">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                Genomic Sequence Scrubber (Chr 7)
              </span>
              <span className="text-[10px] font-mono text-primary">
                Position: 99,352,001 - 99,352,450
              </span>
            </div>
            <div className="h-6 w-full bg-surface-container-highest rounded-sm relative overflow-hidden flex items-center px-1">
              <div className="absolute left-1/4 w-1/3 h-full bg-primary/20 border-x border-primary"></div>
              <div className="flex gap-1 w-full opacity-60">
                {SEQUENCE_MARKERS.map((marker, i) => (
                  <span
                    key={i}
                    className="text-[9px] font-mono w-4 text-center"
                  >
                    {marker}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      <BioChat />

      {/* Background Decoration */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        <div className="absolute top-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-primary/5 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-tertiary/5 blur-[100px]"></div>
      </div>
    </>
  );
}

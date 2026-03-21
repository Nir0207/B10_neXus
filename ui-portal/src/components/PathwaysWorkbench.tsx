"use client";

import { useEffect, useState } from "react";
import BioChat from "@/components/BioChat";
import OrganNavigator from "@/components/OrganNavigator";
import { findNode, scopeTripletsToOrgan, summarizeTriplets } from "@/lib/discovery";
import type { GeneDetail } from "@/services/bioService";
import { bioService } from "@/services/bioService";
import { useBioData } from "@/hooks/useBioData";

export default function PathwaysWorkbench(): React.JSX.Element {
  const [organType, setOrganType] = useState<string>("liver");
  const [selectedGeneId, setSelectedGeneId] = useState<string>("");
  const [geneDetail, setGeneDetail] = useState<GeneDetail | null>(null);
  const [geneError, setGeneError] = useState<string>("");
  const { data, isLoading, isFetching, isError, error, refetch } = useBioData(organType);

  const scopedData = scopeTripletsToOrgan(data, organType);
  const summary = summarizeTriplets(scopedData);

  useEffect(() => {
    const firstGeneId = summary.genes[0]?.properties?.uniprot_id;
    if (typeof firstGeneId === "string" && firstGeneId !== selectedGeneId) {
      setSelectedGeneId(firstGeneId);
    }
  }, [selectedGeneId, summary.genes]);

  useEffect(() => {
    if (!selectedGeneId) {
      setGeneDetail(null);
      setGeneError("");
      return;
    }

    let cancelled = false;
    void bioService
      .fetchGene(selectedGeneId)
      .then((detail) => {
        if (!cancelled) {
          setGeneDetail(detail);
          setGeneError("");
        }
      })
      .catch((fetchError: unknown) => {
        if (!cancelled) {
          setGeneDetail(null);
          setGeneError(
            fetchError instanceof Error ? fetchError.message : "Unable to resolve gene metadata."
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedGeneId]);

  const gatewayError =
    error instanceof Error
      ? error.message
      : "Pathway evidence is unavailable. Verify the gateway and Neo4j services.";

  return (
    <>
      <OrganNavigator
        onExport={() => {
          const payload = JSON.stringify(
            {
              organ: organType,
              summary,
              geneDetail,
            },
            null,
            2
          );
          const blob = new Blob([payload], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `bionexus-${organType}-pathways.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        }}
        selectedOrgan={organType}
        onSelectOrgan={setOrganType}
      />

      <main className="flex-1 overflow-y-auto bg-surface">
        <section className="px-8 py-7 border-b border-outline-variant/10">
          <p className="text-xs uppercase tracking-[0.28em] text-primary mb-3">Pathway Console</p>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div className="max-w-3xl">
              <h1 className="text-3xl font-headline font-bold mb-3">
                Mechanistic review for the {organType} discovery slice
              </h1>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                This route converts the live triplet graph into pathway-focused evidence blocks.
                Gene metadata is resolved from the gateway using UniProt as the primary key.
              </p>
            </div>
            <button
              className="rounded-full border border-outline-variant/20 bg-surface-container-low px-4 py-2 text-xs font-semibold hover:border-primary/40 hover:text-primary transition-colors"
              onClick={() => {
                void refetch();
              }}
              type="button"
            >
              {isFetching ? "Refreshing..." : "Refresh Evidence"}
            </button>
          </div>
        </section>

        {isError ? (
          <div className="m-8 rounded-3xl border border-error/40 bg-error-container/20 p-6 text-sm text-error">
            {gatewayError}
          </div>
        ) : null}

        <section className="grid gap-6 px-8 py-8 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ["Genes", String(summary.genes.length)],
                ["Diseases", String(summary.diseases.length)],
                ["Medicines", String(summary.medicines.length)],
              ].map(([label, value]) => (
                <article
                  className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-5 shadow-xl"
                  key={label}
                >
                  <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">{label}</p>
                  <p className="text-3xl font-headline font-bold">{value}</p>
                </article>
              ))}
            </div>

            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-2">
                    Active Gene Review
                  </p>
                  <h2 className="text-2xl font-headline font-bold">Primary UniProt mapping</h2>
                </div>
                <select
                  className="rounded-2xl border border-outline-variant/20 bg-surface-container-high px-3 py-2 text-sm outline-none"
                  onChange={(event) => setSelectedGeneId(event.target.value)}
                  value={selectedGeneId}
                >
                  {summary.genes.map((gene) => {
                    const uniprotId =
                      typeof gene.properties?.uniprot_id === "string"
                        ? gene.properties.uniprot_id
                        : gene.label;
                    return (
                      <option key={gene.id} value={uniprotId}>
                        {gene.label}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-primary mb-2">Resolved Gene</p>
                  <p className="text-xl font-headline font-bold mb-2">
                    {geneDetail?.gene_symbol ?? "Waiting for gateway lookup"}
                  </p>
                  <p className="text-sm text-on-surface-variant">
                    UniProt: {geneDetail?.uniprot_id ?? (selectedGeneId || "Unavailable")}
                  </p>
                  <p className="text-sm text-on-surface-variant">
                    Source: {geneDetail?.data_source ?? "BioNexus staging"}
                  </p>
                </div>
                <div className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-primary mb-2">Quality Signal</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed">
                    {geneError ||
                      geneDetail?.name ||
                      "The current organ slice has not yielded a gateway-backed gene detail yet."}
                  </p>
                </div>
              </div>
            </article>

            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Mechanistic Chain</p>
              <div className="space-y-3">
                {summary.geneDiseaseEdges.length === 0 ? (
                  <p className="text-sm text-on-surface-variant">
                    {isLoading ? "Loading graph evidence..." : "No gene-disease relationships are available."}
                  </p>
                ) : (
                  summary.geneDiseaseEdges.map((edge) => {
                    const gene = findNode(summary.genes, edge.source);
                    const disease = findNode(summary.diseases, edge.target);
                    return (
                      <div
                        className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4"
                        key={`${edge.source}-${edge.target}-${edge.relationship}`}
                      >
                        <p className="text-sm font-semibold">
                          {gene?.label ?? edge.source} <span className="text-primary">associates with</span>{" "}
                          {disease?.label ?? edge.target}
                        </p>
                        <p className="mt-2 text-xs uppercase tracking-[0.22em] text-on-surface-variant">
                          relationship: {edge.relationship}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </article>
          </div>

          <div className="space-y-6">
            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">
                Therapeutic Overlay
              </p>
              <div className="space-y-3">
                {summary.diseaseMedicineEdges.length === 0 ? (
                  <p className="text-sm text-on-surface-variant">
                    No disease-medicine chain is currently available for this organ slice.
                  </p>
                ) : (
                  summary.diseaseMedicineEdges.map((edge) => {
                    const medicine = findNode(summary.medicines, edge.source);
                    const disease = findNode(summary.diseases, edge.target);
                    return (
                      <div
                        className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4"
                        key={`${edge.source}-${edge.target}-${edge.relationship}`}
                      >
                        <p className="text-sm font-semibold">
                          {medicine?.label ?? edge.source} <span className="text-tertiary">treats</span>{" "}
                          {disease?.label ?? edge.target}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </article>

            <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-xl">
              <p className="text-[10px] uppercase tracking-[0.28em] text-primary mb-3">Binding Evidence</p>
              <div className="space-y-3">
                {summary.medicineGeneEdges.length === 0 ? (
                  <p className="text-sm text-on-surface-variant">
                    No medicine-gene binding edge is currently available.
                  </p>
                ) : (
                  summary.medicineGeneEdges.map((edge) => {
                    const medicine = findNode(summary.medicines, edge.source);
                    const gene = findNode(summary.genes, edge.target);
                    return (
                      <div
                        className="rounded-2xl border border-outline-variant/15 bg-background/60 p-4"
                        key={`${edge.source}-${edge.target}-${edge.relationship}`}
                      >
                        <p className="text-sm font-semibold">
                          {medicine?.label ?? edge.source} <span className="text-primary">binds to</span>{" "}
                          {gene?.label ?? edge.target}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </article>
          </div>
        </section>
      </main>

      <BioChat data={scopedData} organType={organType} />
    </>
  );
}

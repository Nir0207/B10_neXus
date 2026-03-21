import type { BioEdge, BioNode, TripletData } from "@/services/bioService";

export interface DiscoverySummary {
  genes: BioNode[];
  diseases: BioNode[];
  medicines: BioNode[];
  geneDiseaseEdges: BioEdge[];
  diseaseMedicineEdges: BioEdge[];
  medicineGeneEdges: BioEdge[];
}

export function summarizeTriplets(data?: TripletData): DiscoverySummary {
  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];

  return {
    genes: nodes.filter((node) => node.type === "Gene"),
    diseases: nodes.filter((node) => node.type === "Disease"),
    medicines: nodes.filter((node) => node.type === "Medicine"),
    geneDiseaseEdges: edges.filter((edge) => edge.relationship === "ASSOCIATED_WITH"),
    diseaseMedicineEdges: edges.filter((edge) => edge.relationship === "TREATS"),
    medicineGeneEdges: edges.filter((edge) => edge.relationship === "BINDS_TO"),
  };
}

export function findNode(nodes: readonly BioNode[], id: string): BioNode | undefined {
  return nodes.find((node) => node.id === id);
}

export function scopeTripletsToOrgan(
  data: TripletData | undefined,
  organ: string,
): TripletData | undefined {
  if (!data) {
    return data;
  }

  const diseaseNodes = data.nodes.filter((node) => node.type === "Disease");
  if (diseaseNodes.length === 0) {
    return data;
  }

  const hasMatchingDisease = diseaseNodes.some((node) => {
    const nodeOrgan = node.properties?.organ;
    return typeof nodeOrgan === "string" && nodeOrgan.toLowerCase() === organ.toLowerCase();
  });

  return hasMatchingDisease ? data : undefined;
}

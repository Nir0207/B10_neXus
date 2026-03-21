import apiClient from "./api";

export interface BioNode {
  id: string;
  label: string;
  type: "Gene" | "Disease" | "Medicine";
  properties?: Record<string, unknown>;
}

export interface BioEdge {
  source: string;
  target: string;
  relationship: string;
  properties?: Record<string, unknown>;
}

export interface TripletData {
  nodes: BioNode[];
  edges: BioEdge[];
}

export interface GeneDetail {
  data_source: string;
  description?: string | null;
  gene_symbol: string;
  name: string;
  uniprot_id: string;
}

export interface FetchTripletOptions {
  signal?: AbortSignal;
}

export const bioService = {
  fetchTriplets: async (
    organType: string,
    options?: FetchTripletOptions
  ): Promise<TripletData> => {
    try {
      const response = await apiClient.get<TripletData>(`/api/v1/discovery/triplets`, {
        signal: options?.signal,
        params: { organ: organType },
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching triplets for ${organType}`, error);
      throw error;
    }
  },
  fetchGene: async (uniprotId: string, options?: FetchTripletOptions): Promise<GeneDetail> => {
    try {
      const response = await apiClient.get<GeneDetail>(`/api/v1/genes/${uniprotId}`, {
        signal: options?.signal,
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching gene ${uniprotId}`, error);
      throw error;
    }
  },
};

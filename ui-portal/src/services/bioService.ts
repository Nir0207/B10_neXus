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

export interface FetchTripletOptions {
  signal?: AbortSignal;
}

export const bioService = {
  fetchTriplets: async (
    organType: string,
    options?: FetchTripletOptions
  ): Promise<TripletData> => {
    try {
      // Mocked endpoint shape for the UI Portal (requires mapping in API Gateway)
      const response = await apiClient.get<TripletData>(`/api/triplets`, {
        signal: options?.signal,
        params: { organ: organType },
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching triplets for ${organType}`, error);
      throw error;
    }
  },
};

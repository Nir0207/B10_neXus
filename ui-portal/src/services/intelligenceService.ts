import apiClient from "./api";

export interface IntelligenceQueryRequest {
  prompt: string;
  organ?: string;
  gene?: string;
  uniprot_id?: string;
  disease?: string;
  medicine?: string;
  study_id?: string;
}

export interface IntelligenceQueryResponse {
  reply: string;
  mode: string;
  resolved_entity?: string | null;
  sources: string[];
}

export const intelligenceService = {
  query: async (
    payload: IntelligenceQueryRequest,
    signal?: AbortSignal,
  ): Promise<IntelligenceQueryResponse> => {
    const response = await apiClient.post<IntelligenceQueryResponse>(
      "/api/v1/intelligence/query",
      payload,
      { signal, timeout: 45000 }
    );
    return response.data;
  },
};

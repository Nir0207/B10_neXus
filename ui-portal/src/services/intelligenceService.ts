import apiClient from "./api";

export interface VisualPayload {
  chart_type: "line" | "bar" | "radar";
  title: string;
  disease_id: string;
  disease_name: string;
  x_key: string;
  y_key: string;
  datasets: Array<Record<string, string | number>>;
  clinical_summary: string;
}

export interface IntelligenceQueryRequest {
  prompt: string;
  organ?: string;
  gene?: string;
  uniprot_id?: string;
  disease?: string;
  medicine?: string;
  study_id?: string;
  history?: Array<{
    role: "assistant" | "user";
    text: string;
  }>;
}

export interface IntelligenceQueryResponse {
  reply: string;
  mode: string;
  resolved_entity?: string | null;
  sources: string[];
  visual_payload?: VisualPayload | null;
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

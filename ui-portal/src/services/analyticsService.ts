import apiClient from "./api";

export interface FrequencyTimelinePoint {
  year: number;
  study_count: number;
}

export interface GeneDistributionPoint {
  uniprot_id: string;
  gene_symbol: string;
  association_score: number;
  association_source?: string | null;
}

export interface OrganAffinityPoint {
  organ: string;
  value: number;
}

export interface TherapeuticLandscapePoint {
  chembl_id: string;
  molecule_name: string;
  uniprot_id: string;
  gene_symbol: string;
  bioactivity_status: string;
  evidence_source?: string | null;
  affinity?: number | null;
}

export interface TrendAnalyticsResponse {
  disease_id: string;
  disease_name: string;
  clinical_summary: string;
  frequency_timeline: FrequencyTimelinePoint[];
  gene_distribution: GeneDistributionPoint[];
  organ_affinity: OrganAffinityPoint[];
  therapeutic_landscape: TherapeuticLandscapePoint[];
  updated_at?: string | null;
}

export interface ExportChartRequest {
  chart_type: "line" | "bar" | "radar";
  title: string;
  datasets: Array<Record<string, unknown>>;
  clinical_summary: string;
  disease_id?: string;
  disease_name?: string;
  x_key: string;
  y_key: string;
  report_id?: string;
  model_name?: string;
}

export interface ExportHtmlResponse {
  filename: string;
  html: string;
}

export const analyticsService = {
  fetchTrends: async (
    diseaseId: string,
    signal?: AbortSignal,
  ): Promise<TrendAnalyticsResponse> => {
    const response = await apiClient.get<TrendAnalyticsResponse>(
      `/api/v1/analytics/trends/${encodeURIComponent(diseaseId)}`,
      { signal, timeout: 45000 }
    );
    return response.data;
  },

  exportChart: async (
    payload: ExportChartRequest,
    signal?: AbortSignal,
  ): Promise<ExportHtmlResponse> => {
    const response = await apiClient.post<ExportHtmlResponse>(
      "/api/v1/analytics/export",
      payload,
      { signal, timeout: 45000 }
    );
    return response.data;
  },
};

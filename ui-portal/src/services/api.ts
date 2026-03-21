import axios from "axios";
import { clearAuthSession, getStoredToken } from "@/lib/authStorage";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  const headers = axios.AxiosHeaders.from(config.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  config.headers = headers;
  return config;
});

export function toApiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const detail =
      typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : error.message;
    return new Error(detail || "BioNexus gateway request failed.");
  }

  return error instanceof Error ? error : new Error("Unknown BioNexus gateway error");
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      clearAuthSession();
    }

    const normalized = toApiError(error);
    console.error("API call error:", normalized);
    return Promise.reject(normalized);
  }
);

export default apiClient;

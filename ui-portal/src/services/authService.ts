import axios from "axios";
import type { AuthSession } from "@/lib/authStorage";
import { API_BASE_URL, toApiError } from "./api";

interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  fullName?: string;
}

export async function loginWithPassword(username: string, password: string): Promise<AuthSession> {
  try {
    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/token`,
      new URLSearchParams({
        username,
        password,
      }),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout: 10000,
      }
    );

    return {
      token: response.data.access_token,
      username: response.data.username || username,
      issuedAt: new Date().toISOString(),
    };
  } catch (error) {
    throw toApiError(error);
  }
}

export async function registerWithPassword(payload: RegisterPayload): Promise<AuthSession> {
  try {
    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/register`,
      {
        username: payload.username,
        email: payload.email,
        password: payload.password,
        full_name: payload.fullName?.trim() || undefined,
      },
      {
        timeout: 10000,
      }
    );

    return {
      token: response.data.access_token,
      username: response.data.username,
      issuedAt: new Date().toISOString(),
    };
  } catch (error) {
    throw toApiError(error);
  }
}

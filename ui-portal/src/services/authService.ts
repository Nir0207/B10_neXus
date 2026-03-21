import axios from "axios";
import type { AuthSession } from "@/lib/authStorage";
import { API_BASE_URL, toApiError } from "./api";

interface TokenResponse {
  access_token: string;
  token_type: string;
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
      username,
      issuedAt: new Date().toISOString(),
    };
  } catch (error) {
    throw toApiError(error);
  }
}

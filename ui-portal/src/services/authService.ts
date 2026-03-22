import type { AuthSession } from "@/lib/authStorage";
import {
  loginTelemetryUser,
  registerTelemetryUser,
  type RegisterPayload,
} from "@/services/telemetryService";

export type { RegisterPayload } from "@/services/telemetryService";

export async function loginWithPassword(username: string, password: string): Promise<AuthSession> {
  return loginTelemetryUser(username, password);
}

export async function registerWithPassword(payload: RegisterPayload): Promise<AuthSession> {
  return registerTelemetryUser(payload);
}

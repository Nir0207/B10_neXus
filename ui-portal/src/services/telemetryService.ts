"use client";

import axios from "axios";
import { getStoredToken, type AuthSession } from "@/lib/authStorage";

export const TELEMETRY_API_URL =
  process.env.NEXT_PUBLIC_TELEMETRY_API_URL || "http://localhost:4100/graphql";

interface GraphQLErrorPayload {
  message?: string;
}

interface GraphQLResponse<TData> {
  data?: TData;
  errors?: GraphQLErrorPayload[];
}

export interface TelemetryUser {
  id: string;
  username: string;
  email: string;
  fullName?: string | null;
  isAdmin: boolean;
  createdAt: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  fullName?: string;
}

export interface DailyActivityPoint {
  date: string;
  totalEvents: number;
  uniqueUsers: number;
  adminEvents: number;
  nonAdminEvents: number;
}

export interface MetricBucket {
  key: string;
  count: number;
}

export interface RecentTelemetryEvent {
  id: string;
  username: string;
  isAdmin: boolean;
  eventType: string;
  route?: string | null;
  label?: string | null;
  browserName?: string | null;
  deviceType?: string | null;
  createdAt: string;
}

export interface TelemetryDashboardPayload {
  generatedAt: string;
  rangeDays: number;
  totalEvents: number;
  uniqueUsers: number;
  activeRoutes: number;
  averageEventsPerUser: number;
  dailyActivity: DailyActivityPoint[];
  eventComparison: MetricBucket[];
  routeComparison: MetricBucket[];
  browserComparison: MetricBucket[];
  deviceComparison: MetricBucket[];
  userSegmentComparison: MetricBucket[];
  recentEvents: RecentTelemetryEvent[];
}

export interface TelemetryEventInput {
  eventType: string;
  route?: string | null;
  sessionId: string;
  label?: string | null;
  browserName?: string | null;
  osName?: string | null;
  deviceType?: string | null;
  language?: string | null;
  timezone?: string | null;
  referrer?: string | null;
  screenWidth?: number | null;
  screenHeight?: number | null;
  durationMs?: number | null;
  metadata?: Record<string, unknown>;
}

interface AuthPayloadResponse {
  accessToken: string;
  tokenType: string;
  user: TelemetryUser;
}

function toGraphQLError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const graphQLError = error.response?.data?.errors?.[0]?.message;
    const detail =
      typeof graphQLError === "string"
        ? graphQLError
        : typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : error.message;
    return new Error(detail || "Telemetry request failed.");
  }

  return error instanceof Error ? error : new Error("Unknown telemetry request error.");
}

async function requestTelemetryGraphQL<TData, TVariables extends Record<string, unknown>>(
  query: string,
  variables: TVariables,
  token?: string | null,
): Promise<TData> {
  try {
    const response = await axios.post<GraphQLResponse<TData>>(
      TELEMETRY_API_URL,
      {
        query,
        variables,
      },
      {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        timeout: 10000,
      },
    );

    const graphQLError = response.data.errors?.[0]?.message;
    if (graphQLError) {
      throw new Error(graphQLError);
    }

    if (!response.data.data) {
      throw new Error("Telemetry service returned an empty response.");
    }

    return response.data.data;
  } catch (error) {
    throw toGraphQLError(error);
  }
}

function toAuthSession(payload: AuthPayloadResponse): AuthSession {
  return {
    token: payload.accessToken,
    username: payload.user.username,
    email: payload.user.email,
    fullName: payload.user.fullName ?? null,
    isAdmin: payload.user.isAdmin,
    issuedAt: new Date().toISOString(),
  };
}

export async function loginTelemetryUser(
  username: string,
  password: string,
): Promise<AuthSession> {
  const data = await requestTelemetryGraphQL<
    { login: AuthPayloadResponse },
    { input: { username: string; password: string } }
  >(
    `
      mutation Login($input: LoginInput!) {
        login(input: $input) {
          accessToken
          tokenType
          user {
            id
            username
            email
            fullName
            isAdmin
            createdAt
          }
        }
      }
    `,
    {
      input: {
        username,
        password,
      },
    },
  );

  return toAuthSession(data.login);
}

export async function registerTelemetryUser(payload: RegisterPayload): Promise<AuthSession> {
  const data = await requestTelemetryGraphQL<
    { register: AuthPayloadResponse },
    { input: RegisterPayload }
  >(
    `
      mutation Register($input: RegisterInput!) {
        register(input: $input) {
          accessToken
          tokenType
          user {
            id
            username
            email
            fullName
            isAdmin
            createdAt
          }
        }
      }
    `,
    {
      input: {
        username: payload.username,
        email: payload.email,
        password: payload.password,
        fullName: payload.fullName?.trim() || undefined,
      },
    },
  );

  return toAuthSession(data.register);
}

export async function fetchCurrentUser(token?: string | null): Promise<TelemetryUser> {
  const data = await requestTelemetryGraphQL<{ me: TelemetryUser }, Record<string, never>>(
    `
      query Me {
        me {
          id
          username
          email
          fullName
          isAdmin
          createdAt
        }
      }
    `,
    {},
    token ?? getStoredToken(),
  );

  if (!data.me) {
    throw new Error("Authentication required");
  }

  return data.me;
}

export async function recordTelemetryEvent(
  input: TelemetryEventInput,
  token?: string | null,
): Promise<void> {
  await requestTelemetryGraphQL<
    { recordTelemetry: { accepted: boolean; eventId: string } },
    { input: TelemetryEventInput }
  >(
    `
      mutation RecordTelemetry($input: TelemetryInput!) {
        recordTelemetry(input: $input) {
          accepted
          eventId
        }
      }
    `,
    {
      input,
    },
    token ?? getStoredToken(),
  );
}

export async function fetchTelemetryDashboard(
  rangeDays: number,
  token?: string | null,
): Promise<TelemetryDashboardPayload> {
  const data = await requestTelemetryGraphQL<
    { telemetryDashboard: TelemetryDashboardPayload },
    { rangeDays: number }
  >(
    `
      query TelemetryDashboard($rangeDays: Int!) {
        telemetryDashboard(rangeDays: $rangeDays) {
          generatedAt
          rangeDays
          totalEvents
          uniqueUsers
          activeRoutes
          averageEventsPerUser
          dailyActivity {
            date
            totalEvents
            uniqueUsers
            adminEvents
            nonAdminEvents
          }
          eventComparison {
            key
            count
          }
          routeComparison {
            key
            count
          }
          browserComparison {
            key
            count
          }
          deviceComparison {
            key
            count
          }
          userSegmentComparison {
            key
            count
          }
          recentEvents {
            id
            username
            isAdmin
            eventType
            route
            label
            browserName
            deviceType
            createdAt
          }
        }
      }
    `,
    { rangeDays },
    token ?? getStoredToken(),
  );

  return data.telemetryDashboard;
}

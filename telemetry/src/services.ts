import type { AppConfig } from "./config";
import { createAccessToken, decodeAccessToken } from "./security/jwt";
import { hashPassword, normalizeEmail, normalizeUsername, verifyPassword } from "./security/password";
import type {
  AuthTokenClaims,
  PublicUser,
  TelemetryEventInput,
  TelemetryEventRecord,
  TelemetryEventRepository,
  UserRecord,
  UserRepository,
} from "./types";

export class AuthenticationError extends Error {}
export class AuthorizationError extends Error {}
export class ConflictError extends Error {}
export class ValidationError extends Error {}

export interface AuthResult {
  accessToken: string;
  tokenType: "bearer";
  user: PublicUser;
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

export interface TelemetryDashboard {
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
  recentEvents: Array<{
    id: string;
    username: string;
    isAdmin: boolean;
    eventType: string;
    route: string | null;
    label: string | null;
    browserName: string | null;
    deviceType: string | null;
    createdAt: string;
  }>;
}

function toPublicUser(record: UserRecord): PublicUser {
  return {
    id: record.id,
    username: record.username,
    email: record.email,
    fullName: record.fullName,
    isAdmin: record.isAdmin,
    createdAt: record.createdAt,
  };
}

function sortMetricBuckets(buckets: Map<string, number>): MetricBucket[] {
  return [...buckets.entries()]
    .sort((left: [string, number], right: [string, number]) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([key, count]: [string, number]) => ({ key, count }));
}

function increaseBucket(buckets: Map<string, number>, key: string): void {
  const currentValue = buckets.get(key) ?? 0;
  buckets.set(key, currentValue + 1);
}

function dayKey(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function sanitizeText(value: string | null | undefined, maxLength: number): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return null;
  }

  return trimmedValue.slice(0, maxLength);
}

function sanitizeMetadata(metadata: unknown): Record<string, unknown> {
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    return {};
  }

  const sanitizedEntries = Object.entries(metadata as Record<string, unknown>).slice(0, 12);
  return Object.fromEntries(sanitizedEntries);
}

export function sanitizeTelemetryInput(input: TelemetryEventInput): TelemetryEventInput {
  if (!sanitizeText(input.eventType, 64)) {
    throw new ValidationError("Telemetry event type is required");
  }

  if (!sanitizeText(input.sessionId, 128)) {
    throw new ValidationError("Telemetry session id is required");
  }

  return {
    eventType: sanitizeText(input.eventType, 64) ?? "unknown",
    route: sanitizeText(input.route, 160),
    sessionId: sanitizeText(input.sessionId, 128) ?? "unknown",
    label: sanitizeText(input.label, 160),
    browserName: sanitizeText(input.browserName, 80),
    osName: sanitizeText(input.osName, 80),
    deviceType: sanitizeText(input.deviceType, 80),
    language: sanitizeText(input.language, 32),
    timezone: sanitizeText(input.timezone, 64),
    referrer: sanitizeText(input.referrer, 256),
    screenWidth: typeof input.screenWidth === "number" ? input.screenWidth : null,
    screenHeight: typeof input.screenHeight === "number" ? input.screenHeight : null,
    durationMs: typeof input.durationMs === "number" ? input.durationMs : null,
    metadata: sanitizeMetadata(input.metadata),
  };
}

export async function registerUser(
  userRepository: UserRepository,
  config: AppConfig,
  input: {
    username: string;
    email: string;
    password: string;
    fullName?: string | null;
  },
): Promise<AuthResult> {
  const normalizedUsername = normalizeUsername(input.username);
  const normalizedEmail = normalizeEmail(input.email);
  const trimmedFullName = sanitizeText(input.fullName, 120);

  if (!normalizedUsername || normalizedUsername.length < 3) {
    throw new ValidationError("Username must be at least 3 characters");
  }

  if (!normalizedEmail.includes("@")) {
    throw new ValidationError("Email must be valid");
  }

  if (input.password.trim().length < 8) {
    throw new ValidationError("Password must be at least 8 characters");
  }

  const existingUser = await userRepository.findByUsername(normalizedUsername);
  if (existingUser) {
    throw new ConflictError("Username already exists");
  }

  const existingEmail = await userRepository.findByEmail(normalizedEmail);
  if (existingEmail) {
    throw new ConflictError("Email already exists");
  }

  const createdUser = await userRepository.create({
    username: normalizedUsername,
    email: normalizedEmail,
    fullName: trimmedFullName,
    password: hashPassword(input.password),
    isAdmin: false,
  });
  const publicUser = toPublicUser(createdUser);

  return {
    accessToken: createAccessToken(publicUser, config),
    tokenType: "bearer",
    user: publicUser,
  };
}

export async function loginUser(
  userRepository: UserRepository,
  config: AppConfig,
  input: {
    username: string;
    password: string;
  },
): Promise<AuthResult> {
  const normalizedUsername = normalizeUsername(input.username);
  const user = await userRepository.findByUsername(normalizedUsername);
  if (!user || !verifyPassword(input.password, user.hashedPassword)) {
    throw new AuthenticationError("Incorrect username or password");
  }

  const publicUser = toPublicUser(user);
  return {
    accessToken: createAccessToken(publicUser, config),
    tokenType: "bearer",
    user: publicUser,
  };
}

export async function ensureAdminUser(userRepository: UserRepository, config: AppConfig): Promise<void> {
  await userRepository.ensureAdmin({
    username: config.adminUsername,
    email: config.adminEmail,
    fullName: config.adminFullName,
    password: hashPassword(config.adminPassword),
    isAdmin: true,
  });
}

export async function resolveCurrentUser(
  userRepository: UserRepository,
  config: AppConfig,
  token: string | null,
): Promise<PublicUser | null> {
  if (!token) {
    return null;
  }

  let claims: AuthTokenClaims;
  try {
    claims = decodeAccessToken(token, config);
  } catch {
    return null;
  }

  const user = await userRepository.findByUsername(claims.sub);
  return user ? toPublicUser(user) : null;
}

export async function recordTelemetry(
  telemetryRepository: TelemetryEventRepository,
  currentUser: PublicUser | null,
  input: TelemetryEventInput,
): Promise<TelemetryEventRecord> {
  if (!currentUser) {
    throw new AuthenticationError("Authentication required");
  }

  return telemetryRepository.create(currentUser, sanitizeTelemetryInput(input));
}

export function buildTelemetryDashboard(
  events: TelemetryEventRecord[],
  rangeDays: number,
): TelemetryDashboard {
  const dailyBuckets = new Map<string, { totalEvents: number; usernames: Set<string>; adminEvents: number; nonAdminEvents: number }>();
  const eventBuckets = new Map<string, number>();
  const routeBuckets = new Map<string, number>();
  const browserBuckets = new Map<string, number>();
  const deviceBuckets = new Map<string, number>();
  const userSegmentBuckets = new Map<string, number>();
  const usernames = new Set<string>();
  const activeRoutes = new Set<string>();

  for (const event of events) {
    const key = dayKey(event.createdAt);
    const dailyBucket = dailyBuckets.get(key) ?? {
      totalEvents: 0,
      usernames: new Set<string>(),
      adminEvents: 0,
      nonAdminEvents: 0,
    };

    dailyBucket.totalEvents += 1;
    dailyBucket.usernames.add(event.username);
    if (event.isAdmin) {
      dailyBucket.adminEvents += 1;
    } else {
      dailyBucket.nonAdminEvents += 1;
    }
    dailyBuckets.set(key, dailyBucket);

    usernames.add(event.username);
    if (event.route) {
      activeRoutes.add(event.route);
      increaseBucket(routeBuckets, event.route);
    }

    increaseBucket(eventBuckets, event.eventType);
    increaseBucket(browserBuckets, event.browserName ?? "Unknown");
    increaseBucket(deviceBuckets, event.deviceType ?? "Unknown");
    increaseBucket(userSegmentBuckets, event.isAdmin ? "Admin" : "Non-Admin");
  }

  const dailyActivity = [...dailyBuckets.entries()]
    .sort((left: [string, { totalEvents: number }], right: [string, { totalEvents: number }]) =>
      left[0].localeCompare(right[0]),
    )
    .map(([date, bucket]) => ({
      date,
      totalEvents: bucket.totalEvents,
      uniqueUsers: bucket.usernames.size,
      adminEvents: bucket.adminEvents,
      nonAdminEvents: bucket.nonAdminEvents,
    }));

  return {
    generatedAt: new Date().toISOString(),
    rangeDays,
    totalEvents: events.length,
    uniqueUsers: usernames.size,
    activeRoutes: activeRoutes.size,
    averageEventsPerUser: usernames.size > 0 ? Number((events.length / usernames.size).toFixed(2)) : 0,
    dailyActivity,
    eventComparison: sortMetricBuckets(eventBuckets),
    routeComparison: sortMetricBuckets(routeBuckets),
    browserComparison: sortMetricBuckets(browserBuckets),
    deviceComparison: sortMetricBuckets(deviceBuckets),
    userSegmentComparison: sortMetricBuckets(userSegmentBuckets),
    recentEvents: events.slice(0, 12).map((event: TelemetryEventRecord) => ({
      id: event.id,
      username: event.username,
      isAdmin: event.isAdmin,
      eventType: event.eventType,
      route: event.route,
      label: event.label,
      browserName: event.browserName,
      deviceType: event.deviceType,
      createdAt: event.createdAt.toISOString(),
    })),
  };
}

export async function fetchTelemetryDashboard(
  telemetryRepository: TelemetryEventRepository,
  currentUser: PublicUser | null,
  rangeDays: number,
): Promise<TelemetryDashboard> {
  if (!currentUser) {
    throw new AuthenticationError("Authentication required");
  }

  if (!currentUser.isAdmin) {
    throw new AuthorizationError("Admin access required");
  }

  const boundedRange = Math.max(1, Math.min(rangeDays, 30));
  const since = new Date(Date.now() - boundedRange * 24 * 60 * 60 * 1000);
  const events = await telemetryRepository.listSince(since);
  return buildTelemetryDashboard(events, boundedRange);
}

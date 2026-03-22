export interface PublicUser {
  id: string;
  username: string;
  email: string;
  fullName: string | null;
  isAdmin: boolean;
  createdAt: Date;
}

export interface UserRecord extends PublicUser {
  hashedPassword: string;
}

export interface CreateUserInput {
  username: string;
  email: string;
  password: string;
  fullName: string | null;
  isAdmin: boolean;
}

export interface TelemetryEventInput {
  eventType: string;
  route: string | null;
  sessionId: string;
  label: string | null;
  browserName: string | null;
  osName: string | null;
  deviceType: string | null;
  language: string | null;
  timezone: string | null;
  referrer: string | null;
  screenWidth: number | null;
  screenHeight: number | null;
  durationMs: number | null;
  metadata: Record<string, unknown>;
}

export interface TelemetryEventRecord extends TelemetryEventInput {
  id: string;
  username: string;
  isAdmin: boolean;
  createdAt: Date;
}

export interface UserRepository {
  findByUsername(username: string): Promise<UserRecord | null>;
  findByEmail(email: string): Promise<UserRecord | null>;
  create(input: CreateUserInput): Promise<UserRecord>;
  ensureAdmin(input: CreateUserInput): Promise<UserRecord>;
}

export interface TelemetryEventRepository {
  create(user: PublicUser, input: TelemetryEventInput): Promise<TelemetryEventRecord>;
  listSince(since: Date): Promise<TelemetryEventRecord[]>;
}

export interface AuthTokenClaims {
  sub: string;
  email: string;
  full_name?: string;
  is_admin: boolean;
}

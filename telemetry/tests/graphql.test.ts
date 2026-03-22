import request from "supertest";
import { createApp } from "../src/app";
import { getConfig } from "../src/config";
import {
  buildTelemetryDashboard,
  ensureAdminUser,
} from "../src/services";
import {
  hashPassword,
  normalizeEmail,
  normalizeUsername,
} from "../src/security/password";
import type {
  CreateUserInput,
  PublicUser,
  TelemetryEventInput,
  TelemetryEventRecord,
  TelemetryEventRepository,
  UserRecord,
  UserRepository,
} from "../src/types";

class InMemoryUserRepository implements UserRepository {
  private readonly users = new Map<string, UserRecord>();

  public async findByUsername(username: string): Promise<UserRecord | null> {
    return this.users.get(normalizeUsername(username)) ?? null;
  }

  public async findByEmail(email: string): Promise<UserRecord | null> {
    const normalizedEmail = normalizeEmail(email);
    for (const user of this.users.values()) {
      if (user.email === normalizedEmail) {
        return user;
      }
    }

    return null;
  }

  public async create(input: CreateUserInput): Promise<UserRecord> {
    const now = new Date();
    const user: UserRecord = {
      id: `${this.users.size + 1}`,
      username: normalizeUsername(input.username),
      email: normalizeEmail(input.email),
      fullName: input.fullName,
      hashedPassword: input.password,
      isAdmin: input.isAdmin,
      createdAt: now,
    };
    this.users.set(user.username, user);
    return user;
  }

  public async ensureAdmin(input: CreateUserInput): Promise<UserRecord> {
    const existingUser = await this.findByUsername(input.username);
    if (existingUser) {
      const updatedUser: UserRecord = {
        ...existingUser,
        email: normalizeEmail(input.email),
        fullName: input.fullName,
        isAdmin: true,
      };
      this.users.set(updatedUser.username, updatedUser);
      return updatedUser;
    }

    return this.create({ ...input, isAdmin: true });
  }
}

class InMemoryTelemetryRepository implements TelemetryEventRepository {
  private readonly events: TelemetryEventRecord[] = [];

  public async create(user: PublicUser, input: TelemetryEventInput): Promise<TelemetryEventRecord> {
    const event: TelemetryEventRecord = {
      id: `${this.events.length + 1}`,
      username: user.username,
      isAdmin: user.isAdmin,
      eventType: input.eventType,
      route: input.route,
      sessionId: input.sessionId,
      label: input.label,
      browserName: input.browserName,
      osName: input.osName,
      deviceType: input.deviceType,
      language: input.language,
      timezone: input.timezone,
      referrer: input.referrer,
      screenWidth: input.screenWidth,
      screenHeight: input.screenHeight,
      durationMs: input.durationMs,
      metadata: input.metadata,
      createdAt: new Date(Date.now() - this.events.length * 60_000),
    };
    this.events.unshift(event);
    return event;
  }

  public async listSince(since: Date): Promise<TelemetryEventRecord[]> {
    return this.events.filter((event: TelemetryEventRecord) => event.createdAt >= since);
  }
}

describe("telemetry graphql", () => {
  const config = getConfig();
  let userRepository: InMemoryUserRepository;
  let telemetryRepository: InMemoryTelemetryRepository;
  let stop: (() => Promise<void>) | null;
  let agent: ReturnType<typeof request>;

  beforeEach(async () => {
    userRepository = new InMemoryUserRepository();
    telemetryRepository = new InMemoryTelemetryRepository();
    await ensureAdminUser(userRepository, {
      ...config,
      adminUsername: "admin",
      adminEmail: "admin@bionexus.dev",
      adminFullName: "BioNexus Admin",
      adminPassword: "password",
    });

    const createdApp = await createApp({
      config,
      telemetryRepository,
      userRepository,
    });
    agent = request(createdApp.app);
    stop = createdApp.stop;
  });

  afterEach(async () => {
    if (stop) {
      await stop();
      stop = null;
    }
  });

  it("registers a user through graphql and returns an access token", async () => {
    const response = await agent.post("/graphql").send({
      query: `
        mutation Register($input: RegisterInput!) {
          register(input: $input) {
            accessToken
            tokenType
            user {
              username
              email
              isAdmin
            }
          }
        }
      `,
      variables: {
        input: {
          username: "Scientist.One",
          email: "Scientist.One@BioNexus.dev",
          password: "strongpassword",
          fullName: "Scientist One",
        },
      },
    });

    expect(response.status).toBe(200);
    expect(response.body.data.register.tokenType).toBe("bearer");
    expect(response.body.data.register.user.username).toBe("scientist.one");
    expect(response.body.data.register.user.isAdmin).toBe(false);
    expect(response.body.data.register.accessToken).toEqual(expect.any(String));
  });

  it("logs the seeded admin in and resolves the current user", async () => {
    const loginResponse = await agent.post("/graphql").send({
      query: `
        mutation Login($input: LoginInput!) {
          login(input: $input) {
            accessToken
            user {
              username
              isAdmin
            }
          }
        }
      `,
      variables: {
        input: {
          username: "admin",
          password: "password",
        },
      },
    });

    const token = loginResponse.body.data.login.accessToken as string;
    const meResponse = await agent
      .post("/graphql")
      .set("Authorization", `Bearer ${token}`)
      .send({
        query: `
          query {
            me {
              username
              email
              isAdmin
            }
          }
        `,
      });

    expect(meResponse.status).toBe(200);
    expect(meResponse.body.data.me).toEqual({
      username: "admin",
      email: "admin@bionexus.dev",
      isAdmin: true,
    });
  });

  it("records telemetry for an authenticated user and exposes the admin dashboard", async () => {
    await userRepository.create({
      username: "operator",
      email: "operator@bionexus.dev",
      fullName: "Operator",
      password: hashPassword("strongpassword"),
      isAdmin: false,
    });

    const adminLogin = await agent.post("/graphql").send({
      query: `
        mutation {
          login(input: { username: "admin", password: "password" }) {
            accessToken
          }
        }
      `,
    });
    const adminToken = adminLogin.body.data.login.accessToken as string;

    const userLogin = await agent.post("/graphql").send({
      query: `
        mutation {
          login(input: { username: "operator", password: "strongpassword" }) {
            accessToken
          }
        }
      `,
    });
    const userToken = userLogin.body.data.login.accessToken as string;

    await agent
      .post("/graphql")
      .set("Authorization", `Bearer ${userToken}`)
      .send({
        query: `
          mutation Record($input: TelemetryInput!) {
            recordTelemetry(input: $input) {
              accepted
              eventId
            }
          }
        `,
        variables: {
          input: {
            eventType: "page_view",
            route: "/explorer",
            sessionId: "session-1",
            browserName: "Safari",
            deviceType: "desktop",
            metadata: { section: "Explorer" },
          },
        },
      });

    const dashboardResponse = await agent
      .post("/graphql")
      .set("Authorization", `Bearer ${adminToken}`)
      .send({
        query: `
          query {
            telemetryDashboard(rangeDays: 7) {
              totalEvents
              uniqueUsers
              routeComparison {
                key
                count
              }
              userSegmentComparison {
                key
                count
              }
            }
          }
        `,
      });

    expect(dashboardResponse.status).toBe(200);
    expect(dashboardResponse.body.data.telemetryDashboard.totalEvents).toBe(1);
    expect(dashboardResponse.body.data.telemetryDashboard.uniqueUsers).toBe(1);
    expect(dashboardResponse.body.data.telemetryDashboard.routeComparison).toEqual([
      { key: "/explorer", count: 1 },
    ]);
    expect(dashboardResponse.body.data.telemetryDashboard.userSegmentComparison).toEqual([
      { key: "Non-Admin", count: 1 },
    ]);
  });

  it("builds comparative telemetry buckets", () => {
    const dashboard = buildTelemetryDashboard(
      [
        {
          id: "1",
          username: "admin",
          isAdmin: true,
          eventType: "page_view",
          route: "/telemetry",
          sessionId: "s1",
          label: "Telemetry",
          browserName: "Safari",
          osName: "macOS",
          deviceType: "desktop",
          language: "en-IN",
          timezone: "Asia/Kolkata",
          referrer: null,
          screenWidth: 1440,
          screenHeight: 900,
          durationMs: 1200,
          metadata: {},
          createdAt: new Date("2026-03-22T10:00:00.000Z"),
        },
        {
          id: "2",
          username: "operator",
          isAdmin: false,
          eventType: "click",
          route: "/explorer",
          sessionId: "s2",
          label: "Gene card",
          browserName: "Chrome",
          osName: "Windows",
          deviceType: "desktop",
          language: "en-US",
          timezone: "UTC",
          referrer: null,
          screenWidth: 1920,
          screenHeight: 1080,
          durationMs: 400,
          metadata: {},
          createdAt: new Date("2026-03-22T11:00:00.000Z"),
        },
      ],
      7,
    );

    expect(dashboard.totalEvents).toBe(2);
    expect(dashboard.uniqueUsers).toBe(2);
    expect(dashboard.browserComparison).toEqual([
      { key: "Chrome", count: 1 },
      { key: "Safari", count: 1 },
    ]);
    expect(dashboard.userSegmentComparison).toEqual([
      { key: "Admin", count: 1 },
      { key: "Non-Admin", count: 1 },
    ]);
  });
});

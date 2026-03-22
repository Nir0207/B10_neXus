import cors from "cors";
import express, { type Request, type Response } from "express";
import { ApolloServer } from "@apollo/server";
import { expressMiddleware } from "@as-integrations/express5";
import GraphQLJSON from "graphql-type-json";
import type { AppConfig } from "./config";
import {
  AuthenticationError,
  AuthorizationError,
  ConflictError,
  ValidationError,
  fetchTelemetryDashboard,
  loginUser,
  recordTelemetry,
  registerUser,
  resolveCurrentUser,
} from "./services";
import type { PublicUser, TelemetryEventRepository, UserRepository } from "./types";

export interface AppDependencies {
  config: AppConfig;
  telemetryRepository: TelemetryEventRepository;
  userRepository: UserRepository;
}

interface GraphQLContext {
  config: AppConfig;
  currentUser: PublicUser | null;
  telemetryRepository: TelemetryEventRepository;
  userRepository: UserRepository;
}

const typeDefs = `#graphql
  scalar JSON

  type User {
    id: ID!
    username: String!
    email: String!
    fullName: String
    isAdmin: Boolean!
    createdAt: String!
  }

  type AuthPayload {
    accessToken: String!
    tokenType: String!
    user: User!
  }

  input RegisterInput {
    username: String!
    email: String!
    password: String!
    fullName: String
  }

  input LoginInput {
    username: String!
    password: String!
  }

  input TelemetryInput {
    eventType: String!
    route: String
    sessionId: String!
    label: String
    browserName: String
    osName: String
    deviceType: String
    language: String
    timezone: String
    referrer: String
    screenWidth: Int
    screenHeight: Int
    durationMs: Int
    metadata: JSON
  }

  type TelemetryMutationResult {
    accepted: Boolean!
    eventId: ID!
  }

  type MetricBucket {
    key: String!
    count: Int!
  }

  type DailyActivityPoint {
    date: String!
    totalEvents: Int!
    uniqueUsers: Int!
    adminEvents: Int!
    nonAdminEvents: Int!
  }

  type RecentTelemetryEvent {
    id: ID!
    username: String!
    isAdmin: Boolean!
    eventType: String!
    route: String
    label: String
    browserName: String
    deviceType: String
    createdAt: String!
  }

  type TelemetryDashboard {
    generatedAt: String!
    rangeDays: Int!
    totalEvents: Int!
    uniqueUsers: Int!
    activeRoutes: Int!
    averageEventsPerUser: Float!
    dailyActivity: [DailyActivityPoint!]!
    eventComparison: [MetricBucket!]!
    routeComparison: [MetricBucket!]!
    browserComparison: [MetricBucket!]!
    deviceComparison: [MetricBucket!]!
    userSegmentComparison: [MetricBucket!]!
    recentEvents: [RecentTelemetryEvent!]!
  }

  type Query {
    me: User
    telemetryDashboard(rangeDays: Int = 7): TelemetryDashboard!
  }

  type Mutation {
    login(input: LoginInput!): AuthPayload!
    register(input: RegisterInput!): AuthPayload!
    recordTelemetry(input: TelemetryInput!): TelemetryMutationResult!
  }
`;

const resolvers = {
  JSON: GraphQLJSON,
  Query: {
    me: async (_parent: unknown, _args: unknown, context: GraphQLContext): Promise<PublicUser | null> =>
      context.currentUser,
    telemetryDashboard: async (
      _parent: unknown,
      args: { rangeDays?: number },
      context: GraphQLContext,
    ) => fetchTelemetryDashboard(context.telemetryRepository, context.currentUser, args.rangeDays ?? 7),
  },
  Mutation: {
    login: async (
      _parent: unknown,
      args: { input: { username: string; password: string } },
      context: GraphQLContext,
    ) => loginUser(context.userRepository, context.config, args.input),
    register: async (
      _parent: unknown,
      args: { input: { username: string; email: string; password: string; fullName?: string | null } },
      context: GraphQLContext,
    ) => registerUser(context.userRepository, context.config, args.input),
    recordTelemetry: async (
      _parent: unknown,
      args: { input: Parameters<typeof recordTelemetry>[2] },
      context: GraphQLContext,
    ) => {
      const event = await recordTelemetry(context.telemetryRepository, context.currentUser, args.input);
      return { accepted: true, eventId: event.id };
    },
  },
  User: {
    createdAt: (user: PublicUser): string => user.createdAt.toISOString(),
  },
};

function toGraphQLError(error: unknown): Error {
  if (
    error instanceof AuthenticationError ||
    error instanceof AuthorizationError ||
    error instanceof ConflictError ||
    error instanceof ValidationError
  ) {
    return new Error(error.message);
  }

  return error instanceof Error ? error : new Error("Unknown telemetry error");
}

export async function createApp(dependencies: AppDependencies): Promise<{
  app: express.Express;
  stop: () => Promise<void>;
}> {
  const app = express();
  const apolloServer = new ApolloServer<GraphQLContext>({
    typeDefs,
    resolvers,
    formatError: (formattedError) => formattedError,
  });

  await apolloServer.start();

  app.use(
    cors({
      origin: dependencies.config.corsAllowOrigins,
      credentials: false,
    }),
  );
  app.use(express.json({ limit: "1mb" }));
  app.get("/health", (_request: Request, response: Response) => {
    response.json({ status: "ok" });
  });
  app.use(
    "/graphql",
    expressMiddleware(apolloServer, {
      context: async ({ req }): Promise<GraphQLContext> => {
        const authHeader = req.headers.authorization;
        const bearerToken = typeof authHeader === "string" && authHeader.startsWith("Bearer ")
          ? authHeader.slice("Bearer ".length)
          : null;

        const currentUser = await resolveCurrentUser(
          dependencies.userRepository,
          dependencies.config,
          bearerToken,
        );

        return {
          config: dependencies.config,
          currentUser,
          telemetryRepository: dependencies.telemetryRepository,
          userRepository: dependencies.userRepository,
        };
      },
    }),
  );

  app.use((error: unknown, _request: Request, response: Response, _next: unknown) => {
    const normalizedError = toGraphQLError(error);
    response.status(500).json({ errors: [{ message: normalizedError.message }] });
  });

  return {
    app,
    stop: async () => {
      await apolloServer.stop();
    },
  };
}

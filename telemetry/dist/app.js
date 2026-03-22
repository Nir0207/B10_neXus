"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createApp = createApp;
const cors_1 = __importDefault(require("cors"));
const express_1 = __importDefault(require("express"));
const server_1 = require("@apollo/server");
const express5_1 = require("@as-integrations/express5");
const graphql_type_json_1 = __importDefault(require("graphql-type-json"));
const services_1 = require("./services");
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
    JSON: graphql_type_json_1.default,
    Query: {
        me: async (_parent, _args, context) => context.currentUser,
        telemetryDashboard: async (_parent, args, context) => (0, services_1.fetchTelemetryDashboard)(context.telemetryRepository, context.currentUser, args.rangeDays ?? 7),
    },
    Mutation: {
        login: async (_parent, args, context) => (0, services_1.loginUser)(context.userRepository, context.config, args.input),
        register: async (_parent, args, context) => (0, services_1.registerUser)(context.userRepository, context.config, args.input),
        recordTelemetry: async (_parent, args, context) => {
            const event = await (0, services_1.recordTelemetry)(context.telemetryRepository, context.currentUser, args.input);
            return { accepted: true, eventId: event.id };
        },
    },
    User: {
        createdAt: (user) => user.createdAt.toISOString(),
    },
};
function toGraphQLError(error) {
    if (error instanceof services_1.AuthenticationError ||
        error instanceof services_1.AuthorizationError ||
        error instanceof services_1.ConflictError ||
        error instanceof services_1.ValidationError) {
        return new Error(error.message);
    }
    return error instanceof Error ? error : new Error("Unknown telemetry error");
}
async function createApp(dependencies) {
    const app = (0, express_1.default)();
    const apolloServer = new server_1.ApolloServer({
        typeDefs,
        resolvers,
        formatError: (formattedError) => formattedError,
    });
    await apolloServer.start();
    app.use((0, cors_1.default)({
        origin: dependencies.config.corsAllowOrigins,
        credentials: false,
    }));
    app.use(express_1.default.json({ limit: "1mb" }));
    app.get("/health", (_request, response) => {
        response.json({ status: "ok" });
    });
    app.use("/graphql", (0, express5_1.expressMiddleware)(apolloServer, {
        context: async ({ req }) => {
            const authHeader = req.headers.authorization;
            const bearerToken = typeof authHeader === "string" && authHeader.startsWith("Bearer ")
                ? authHeader.slice("Bearer ".length)
                : null;
            const currentUser = await (0, services_1.resolveCurrentUser)(dependencies.userRepository, dependencies.config, bearerToken);
            return {
                config: dependencies.config,
                currentUser,
                telemetryRepository: dependencies.telemetryRepository,
                userRepository: dependencies.userRepository,
            };
        },
    }));
    app.use((error, _request, response, _next) => {
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

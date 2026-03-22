"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ValidationError = exports.ConflictError = exports.AuthorizationError = exports.AuthenticationError = void 0;
exports.sanitizeTelemetryInput = sanitizeTelemetryInput;
exports.registerUser = registerUser;
exports.loginUser = loginUser;
exports.ensureAdminUser = ensureAdminUser;
exports.resolveCurrentUser = resolveCurrentUser;
exports.recordTelemetry = recordTelemetry;
exports.buildTelemetryDashboard = buildTelemetryDashboard;
exports.fetchTelemetryDashboard = fetchTelemetryDashboard;
const jwt_1 = require("./security/jwt");
const password_1 = require("./security/password");
class AuthenticationError extends Error {
}
exports.AuthenticationError = AuthenticationError;
class AuthorizationError extends Error {
}
exports.AuthorizationError = AuthorizationError;
class ConflictError extends Error {
}
exports.ConflictError = ConflictError;
class ValidationError extends Error {
}
exports.ValidationError = ValidationError;
function toPublicUser(record) {
    return {
        id: record.id,
        username: record.username,
        email: record.email,
        fullName: record.fullName,
        isAdmin: record.isAdmin,
        createdAt: record.createdAt,
    };
}
function sortMetricBuckets(buckets) {
    return [...buckets.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .map(([key, count]) => ({ key, count }));
}
function increaseBucket(buckets, key) {
    const currentValue = buckets.get(key) ?? 0;
    buckets.set(key, currentValue + 1);
}
function dayKey(value) {
    return value.toISOString().slice(0, 10);
}
function sanitizeText(value, maxLength) {
    if (typeof value !== "string") {
        return null;
    }
    const trimmedValue = value.trim();
    if (!trimmedValue) {
        return null;
    }
    return trimmedValue.slice(0, maxLength);
}
function sanitizeMetadata(metadata) {
    if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
        return {};
    }
    const sanitizedEntries = Object.entries(metadata).slice(0, 12);
    return Object.fromEntries(sanitizedEntries);
}
function sanitizeTelemetryInput(input) {
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
async function registerUser(userRepository, config, input) {
    const normalizedUsername = (0, password_1.normalizeUsername)(input.username);
    const normalizedEmail = (0, password_1.normalizeEmail)(input.email);
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
        password: (0, password_1.hashPassword)(input.password),
        isAdmin: false,
    });
    const publicUser = toPublicUser(createdUser);
    return {
        accessToken: (0, jwt_1.createAccessToken)(publicUser, config),
        tokenType: "bearer",
        user: publicUser,
    };
}
async function loginUser(userRepository, config, input) {
    const normalizedUsername = (0, password_1.normalizeUsername)(input.username);
    const user = await userRepository.findByUsername(normalizedUsername);
    if (!user || !(0, password_1.verifyPassword)(input.password, user.hashedPassword)) {
        throw new AuthenticationError("Incorrect username or password");
    }
    const publicUser = toPublicUser(user);
    return {
        accessToken: (0, jwt_1.createAccessToken)(publicUser, config),
        tokenType: "bearer",
        user: publicUser,
    };
}
async function ensureAdminUser(userRepository, config) {
    await userRepository.ensureAdmin({
        username: config.adminUsername,
        email: config.adminEmail,
        fullName: config.adminFullName,
        password: (0, password_1.hashPassword)(config.adminPassword),
        isAdmin: true,
    });
}
async function resolveCurrentUser(userRepository, config, token) {
    if (!token) {
        return null;
    }
    let claims;
    try {
        claims = (0, jwt_1.decodeAccessToken)(token, config);
    }
    catch {
        return null;
    }
    const user = await userRepository.findByUsername(claims.sub);
    return user ? toPublicUser(user) : null;
}
async function recordTelemetry(telemetryRepository, currentUser, input) {
    if (!currentUser) {
        throw new AuthenticationError("Authentication required");
    }
    return telemetryRepository.create(currentUser, sanitizeTelemetryInput(input));
}
function buildTelemetryDashboard(events, rangeDays) {
    const dailyBuckets = new Map();
    const eventBuckets = new Map();
    const routeBuckets = new Map();
    const browserBuckets = new Map();
    const deviceBuckets = new Map();
    const userSegmentBuckets = new Map();
    const usernames = new Set();
    const activeRoutes = new Set();
    for (const event of events) {
        const key = dayKey(event.createdAt);
        const dailyBucket = dailyBuckets.get(key) ?? {
            totalEvents: 0,
            usernames: new Set(),
            adminEvents: 0,
            nonAdminEvents: 0,
        };
        dailyBucket.totalEvents += 1;
        dailyBucket.usernames.add(event.username);
        if (event.isAdmin) {
            dailyBucket.adminEvents += 1;
        }
        else {
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
        .sort((left, right) => left[0].localeCompare(right[0]))
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
        recentEvents: events.slice(0, 12).map((event) => ({
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
async function fetchTelemetryDashboard(telemetryRepository, currentUser, rangeDays) {
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

"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.MongoTelemetryEventRepository = exports.MongoUserRepository = void 0;
exports.connectToMongo = connectToMongo;
exports.disconnectFromMongo = disconnectFromMongo;
const mongoose_1 = __importDefault(require("mongoose"));
const password_1 = require("./security/password");
const userSchema = new mongoose_1.default.Schema({
    username: { type: String, required: true, unique: true, index: true },
    email: { type: String, required: true, unique: true, index: true },
    fullName: { type: String, required: false, default: null },
    hashedPassword: { type: String, required: true },
    isAdmin: { type: Boolean, required: true, default: false, index: true },
}, {
    collection: "users",
    timestamps: true,
});
const telemetrySchema = new mongoose_1.default.Schema({
    username: { type: String, required: true, index: true },
    isAdmin: { type: Boolean, required: true, default: false, index: true },
    eventType: { type: String, required: true, index: true },
    route: { type: String, required: false, default: null, index: true },
    sessionId: { type: String, required: true, index: true },
    label: { type: String, required: false, default: null },
    browserName: { type: String, required: false, default: null, index: true },
    osName: { type: String, required: false, default: null },
    deviceType: { type: String, required: false, default: null, index: true },
    language: { type: String, required: false, default: null },
    timezone: { type: String, required: false, default: null },
    referrer: { type: String, required: false, default: null },
    screenWidth: { type: Number, required: false, default: null },
    screenHeight: { type: Number, required: false, default: null },
    durationMs: { type: Number, required: false, default: null },
    metadata: { type: mongoose_1.default.Schema.Types.Mixed, required: true, default: {} },
}, {
    collection: "telemetry_events",
    timestamps: { createdAt: true, updatedAt: true },
});
const UserModel = mongoose_1.default.models.User ?? mongoose_1.default.model("User", userSchema);
const TelemetryModel = mongoose_1.default.models.TelemetryEvent ??
    mongoose_1.default.model("TelemetryEvent", telemetrySchema);
function toPublicUser(document) {
    return {
        id: String(document._id),
        username: document.username,
        email: document.email,
        fullName: document.fullName ?? null,
        isAdmin: document.isAdmin,
        createdAt: document.createdAt,
    };
}
function toUserRecord(document) {
    return {
        ...toPublicUser(document),
        hashedPassword: document.hashedPassword,
    };
}
function toTelemetryRecord(document) {
    return {
        id: String(document._id),
        username: document.username,
        isAdmin: document.isAdmin,
        eventType: document.eventType,
        route: document.route ?? null,
        sessionId: document.sessionId,
        label: document.label ?? null,
        browserName: document.browserName ?? null,
        osName: document.osName ?? null,
        deviceType: document.deviceType ?? null,
        language: document.language ?? null,
        timezone: document.timezone ?? null,
        referrer: document.referrer ?? null,
        screenWidth: document.screenWidth ?? null,
        screenHeight: document.screenHeight ?? null,
        durationMs: document.durationMs ?? null,
        metadata: document.metadata ?? {},
        createdAt: document.createdAt,
    };
}
async function connectToMongo(config) {
    if (mongoose_1.default.connection.readyState === 1) {
        return;
    }
    await mongoose_1.default.connect(config.mongodbUri);
}
async function disconnectFromMongo() {
    if (mongoose_1.default.connection.readyState === 0) {
        return;
    }
    await mongoose_1.default.disconnect();
}
class MongoUserRepository {
    async findByUsername(username) {
        const document = await UserModel.findOne({
            username: (0, password_1.normalizeUsername)(username),
        }).lean();
        return document ? toUserRecord(document) : null;
    }
    async findByEmail(email) {
        const document = await UserModel.findOne({
            email: (0, password_1.normalizeEmail)(email),
        }).lean();
        return document ? toUserRecord(document) : null;
    }
    async create(input) {
        const document = await UserModel.create({
            username: (0, password_1.normalizeUsername)(input.username),
            email: (0, password_1.normalizeEmail)(input.email),
            fullName: input.fullName,
            hashedPassword: input.password,
            isAdmin: input.isAdmin,
        });
        return toUserRecord(document.toObject());
    }
    async ensureAdmin(input) {
        const normalizedUsername = (0, password_1.normalizeUsername)(input.username);
        const normalizedEmail = (0, password_1.normalizeEmail)(input.email);
        const existingUser = await UserModel.findOneAndUpdate({ username: normalizedUsername }, {
            $setOnInsert: {
                username: normalizedUsername,
                hashedPassword: input.password,
            },
            $set: {
                email: normalizedEmail,
                fullName: input.fullName,
                isAdmin: true,
            },
        }, {
            upsert: true,
            new: true,
        }).lean();
        if (!existingUser) {
            throw new Error("Failed to ensure admin user");
        }
        return toUserRecord(existingUser);
    }
}
exports.MongoUserRepository = MongoUserRepository;
class MongoTelemetryEventRepository {
    async create(user, input) {
        const document = await TelemetryModel.create({
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
        });
        return toTelemetryRecord(document.toObject());
    }
    async listSince(since) {
        const documents = await TelemetryModel.find({
            createdAt: { $gte: since },
        })
            .sort({ createdAt: -1 })
            .lean();
        return documents.map((document) => toTelemetryRecord(document));
    }
}
exports.MongoTelemetryEventRepository = MongoTelemetryEventRepository;

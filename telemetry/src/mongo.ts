import mongoose from "mongoose";
import type { AppConfig } from "./config";
import type {
  CreateUserInput,
  PublicUser,
  TelemetryEventInput,
  TelemetryEventRecord,
  TelemetryEventRepository,
  UserRecord,
  UserRepository,
} from "./types";
import { normalizeEmail, normalizeUsername } from "./security/password";

interface UserDocument {
  username: string;
  email: string;
  fullName?: string | null;
  hashedPassword: string;
  isAdmin: boolean;
  createdAt: Date;
  updatedAt: Date;
}

interface TelemetryDocument {
  username: string;
  isAdmin: boolean;
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
  metadata: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

const userSchema = new mongoose.Schema<UserDocument>(
  {
    username: { type: String, required: true, unique: true, index: true },
    email: { type: String, required: true, unique: true, index: true },
    fullName: { type: String, required: false, default: null },
    hashedPassword: { type: String, required: true },
    isAdmin: { type: Boolean, required: true, default: false, index: true },
  },
  {
    collection: "users",
    timestamps: true,
  },
);

const telemetrySchema = new mongoose.Schema<TelemetryDocument>(
  {
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
    metadata: { type: mongoose.Schema.Types.Mixed, required: true, default: {} },
  },
  {
    collection: "telemetry_events",
    timestamps: { createdAt: true, updatedAt: true },
  },
);

const UserModel =
  mongoose.models.User ?? mongoose.model<UserDocument>("User", userSchema);
const TelemetryModel =
  mongoose.models.TelemetryEvent ??
  mongoose.model<TelemetryDocument>("TelemetryEvent", telemetrySchema);

function toPublicUser(document: UserDocument & { _id: mongoose.Types.ObjectId }): PublicUser {
  return {
    id: String(document._id),
    username: document.username,
    email: document.email,
    fullName: document.fullName ?? null,
    isAdmin: document.isAdmin,
    createdAt: document.createdAt,
  };
}

function toUserRecord(document: UserDocument & { _id: mongoose.Types.ObjectId }): UserRecord {
  return {
    ...toPublicUser(document),
    hashedPassword: document.hashedPassword,
  };
}

function toTelemetryRecord(
  document: TelemetryDocument & { _id: mongoose.Types.ObjectId },
): TelemetryEventRecord {
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

export async function connectToMongo(config: AppConfig): Promise<void> {
  if (mongoose.connection.readyState === 1) {
    return;
  }

  await mongoose.connect(config.mongodbUri);
}

export async function disconnectFromMongo(): Promise<void> {
  if (mongoose.connection.readyState === 0) {
    return;
  }

  await mongoose.disconnect();
}

export class MongoUserRepository implements UserRepository {
  public async findByUsername(username: string): Promise<UserRecord | null> {
    const document = await UserModel.findOne({
      username: normalizeUsername(username),
    }).lean<UserDocument & { _id: mongoose.Types.ObjectId } | null>();

    return document ? toUserRecord(document) : null;
  }

  public async findByEmail(email: string): Promise<UserRecord | null> {
    const document = await UserModel.findOne({
      email: normalizeEmail(email),
    }).lean<UserDocument & { _id: mongoose.Types.ObjectId } | null>();

    return document ? toUserRecord(document) : null;
  }

  public async create(input: CreateUserInput): Promise<UserRecord> {
    const document = await UserModel.create({
      username: normalizeUsername(input.username),
      email: normalizeEmail(input.email),
      fullName: input.fullName,
      hashedPassword: input.password,
      isAdmin: input.isAdmin,
    });

    return toUserRecord(document.toObject() as UserDocument & { _id: mongoose.Types.ObjectId });
  }

  public async ensureAdmin(input: CreateUserInput): Promise<UserRecord> {
    const normalizedUsername = normalizeUsername(input.username);
    const normalizedEmail = normalizeEmail(input.email);

    const existingUser = await UserModel.findOneAndUpdate(
      { username: normalizedUsername },
      {
        $setOnInsert: {
          username: normalizedUsername,
          hashedPassword: input.password,
        },
        $set: {
          email: normalizedEmail,
          fullName: input.fullName,
          isAdmin: true,
        },
      },
      {
        upsert: true,
        new: true,
      },
    ).lean<UserDocument & { _id: mongoose.Types.ObjectId }>();

    if (!existingUser) {
      throw new Error("Failed to ensure admin user");
    }

    return toUserRecord(existingUser);
  }
}

export class MongoTelemetryEventRepository implements TelemetryEventRepository {
  public async create(user: PublicUser, input: TelemetryEventInput): Promise<TelemetryEventRecord> {
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

    return toTelemetryRecord(document.toObject() as TelemetryDocument & { _id: mongoose.Types.ObjectId });
  }

  public async listSince(since: Date): Promise<TelemetryEventRecord[]> {
    const documents = await TelemetryModel.find({
      createdAt: { $gte: since },
    })
      .sort({ createdAt: -1 })
      .lean<Array<TelemetryDocument & { _id: mongoose.Types.ObjectId }>>();

    return documents.map((document: TelemetryDocument & { _id: mongoose.Types.ObjectId }) =>
      toTelemetryRecord(document),
    );
  }
}

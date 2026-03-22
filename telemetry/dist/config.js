"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getConfig = getConfig;
const path_1 = __importDefault(require("path"));
const dotenv_1 = __importDefault(require("dotenv"));
let configLoaded = false;
function loadEnvironment() {
    if (configLoaded) {
        return;
    }
    const candidatePaths = [
        path_1.default.resolve(process.cwd(), ".env"),
        path_1.default.resolve(process.cwd(), "../.env"),
    ];
    for (const candidatePath of candidatePaths) {
        dotenv_1.default.config({ path: candidatePath, override: false, quiet: true });
    }
    configLoaded = true;
}
function readInteger(name, defaultValue) {
    const rawValue = process.env[name];
    if (!rawValue) {
        return defaultValue;
    }
    const parsedValue = Number.parseInt(rawValue, 10);
    return Number.isFinite(parsedValue) ? parsedValue : defaultValue;
}
function getConfig() {
    loadEnvironment();
    return {
        port: readInteger("PORT", 4100),
        mongodbUri: process.env.MONGODB_URI?.trim() ??
            "mongodb://bionexus_admin:bionexus_dev_password@localhost:27017/bionexus?authSource=admin",
        corsAllowOrigins: (process.env.CORS_ALLOW_ORIGINS ?? "http://localhost:3000,http://127.0.0.1:3000")
            .split(",")
            .map((origin) => origin.trim())
            .filter((origin) => origin.length > 0),
        jwtSecret: process.env.SECRET_KEY?.trim() ?? "super-secret-local-dev-key",
        jwtIssuer: process.env.JWT_ISSUER?.trim() ?? "bionexus-api-gateway",
        jwtAudience: process.env.JWT_AUDIENCE?.trim() ?? "bionexus-ui",
        accessTokenExpireMinutes: readInteger("ACCESS_TOKEN_EXPIRE_MINUTES", 30),
        adminUsername: (process.env.TELEMETRY_ADMIN_USERNAME ?? process.env.GATEWAY_ADMIN_USERNAME ?? "admin").trim(),
        adminPassword: (process.env.TELEMETRY_ADMIN_PASSWORD ?? process.env.GATEWAY_ADMIN_PASSWORD ?? "password").trim(),
        adminEmail: (process.env.TELEMETRY_ADMIN_EMAIL ?? "admin@bionexus.dev").trim(),
        adminFullName: (process.env.TELEMETRY_ADMIN_FULL_NAME ?? "BioNexus Admin").trim(),
    };
}

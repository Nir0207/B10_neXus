import path from "path";
import dotenv from "dotenv";

let configLoaded = false;

function loadEnvironment(): void {
  if (configLoaded) {
    return;
  }

  const candidatePaths = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "../.env"),
  ];

  for (const candidatePath of candidatePaths) {
    dotenv.config({ path: candidatePath, override: false, quiet: true });
  }

  configLoaded = true;
}

function readInteger(name: string, defaultValue: number): number {
  const rawValue = process.env[name];
  if (!rawValue) {
    return defaultValue;
  }

  const parsedValue = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsedValue) ? parsedValue : defaultValue;
}

export interface AppConfig {
  port: number;
  mongodbUri: string;
  corsAllowOrigins: string[];
  jwtSecret: string;
  jwtIssuer: string;
  jwtAudience: string;
  accessTokenExpireMinutes: number;
  adminUsername: string;
  adminPassword: string;
  adminEmail: string;
  adminFullName: string;
}

export function getConfig(): AppConfig {
  loadEnvironment();

  return {
    port: readInteger("PORT", 4100),
    mongodbUri:
      process.env.MONGODB_URI?.trim() ??
      "mongodb://bionexus_admin:bionexus_dev_password@localhost:27017/bionexus?authSource=admin",
    corsAllowOrigins: (process.env.CORS_ALLOW_ORIGINS ?? "http://localhost:3000,http://127.0.0.1:3000")
      .split(",")
      .map((origin: string) => origin.trim())
      .filter((origin: string) => origin.length > 0),
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

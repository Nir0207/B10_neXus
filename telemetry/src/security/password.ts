import crypto from "crypto";

const PBKDF2_PREFIX = "pbkdf2_sha256";

function padBase64(value: string): string {
  const paddingLength = (4 - (value.length % 4)) % 4;
  return `${value}${"=".repeat(paddingLength)}`;
}

export function normalizeUsername(username: string): string {
  return username.trim().toLowerCase();
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const iterations = 390_000;
  const digest = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256");
  const encoded = digest.toString("base64url");
  return `${PBKDF2_PREFIX}$${iterations}$${salt}$${encoded}`;
}

export function verifyPassword(plainPassword: string, hashedPassword: string): boolean {
  if (!hashedPassword.startsWith(`${PBKDF2_PREFIX}$`)) {
    return crypto.timingSafeEqual(
      Buffer.from(plainPassword, "utf8"),
      Buffer.from(hashedPassword, "utf8"),
    );
  }

  const segments = hashedPassword.split("$");
  if (segments.length !== 4) {
    return false;
  }

  const iterations = Number.parseInt(segments[1] ?? "", 10);
  const salt = segments[2] ?? "";
  const encodedHash = segments[3] ?? "";
  if (!Number.isFinite(iterations) || !salt || !encodedHash) {
    return false;
  }

  const candidate = crypto.pbkdf2Sync(plainPassword, salt, iterations, 32, "sha256");
  const expected = Buffer.from(padBase64(encodedHash), "base64url");
  return candidate.length === expected.length && crypto.timingSafeEqual(candidate, expected);
}

"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeUsername = normalizeUsername;
exports.normalizeEmail = normalizeEmail;
exports.hashPassword = hashPassword;
exports.verifyPassword = verifyPassword;
const crypto_1 = __importDefault(require("crypto"));
const PBKDF2_PREFIX = "pbkdf2_sha256";
function padBase64(value) {
    const paddingLength = (4 - (value.length % 4)) % 4;
    return `${value}${"=".repeat(paddingLength)}`;
}
function normalizeUsername(username) {
    return username.trim().toLowerCase();
}
function normalizeEmail(email) {
    return email.trim().toLowerCase();
}
function hashPassword(password) {
    const salt = crypto_1.default.randomBytes(16).toString("hex");
    const iterations = 390_000;
    const digest = crypto_1.default.pbkdf2Sync(password, salt, iterations, 32, "sha256");
    const encoded = digest.toString("base64url");
    return `${PBKDF2_PREFIX}$${iterations}$${salt}$${encoded}`;
}
function verifyPassword(plainPassword, hashedPassword) {
    if (!hashedPassword.startsWith(`${PBKDF2_PREFIX}$`)) {
        return crypto_1.default.timingSafeEqual(Buffer.from(plainPassword, "utf8"), Buffer.from(hashedPassword, "utf8"));
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
    const candidate = crypto_1.default.pbkdf2Sync(plainPassword, salt, iterations, 32, "sha256");
    const expected = Buffer.from(padBase64(encodedHash), "base64url");
    return candidate.length === expected.length && crypto_1.default.timingSafeEqual(candidate, expected);
}

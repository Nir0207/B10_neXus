"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createAccessToken = createAccessToken;
exports.decodeAccessToken = decodeAccessToken;
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
function createAccessToken(user, config) {
    return jsonwebtoken_1.default.sign({
        email: user.email,
        full_name: user.fullName ?? undefined,
        is_admin: user.isAdmin,
    }, config.jwtSecret, {
        algorithm: "HS256",
        issuer: config.jwtIssuer,
        audience: config.jwtAudience,
        expiresIn: `${config.accessTokenExpireMinutes}m`,
        subject: user.username,
    });
}
function decodeAccessToken(token, config) {
    const decodedToken = jsonwebtoken_1.default.verify(token, config.jwtSecret, {
        algorithms: ["HS256"],
        issuer: config.jwtIssuer,
        audience: config.jwtAudience,
    });
    if (typeof decodedToken !== "object" || decodedToken === null) {
        throw new Error("Invalid JWT payload");
    }
    return {
        sub: String(decodedToken.sub ?? ""),
        email: String(decodedToken.email ?? ""),
        full_name: typeof decodedToken.full_name === "string" && decodedToken.full_name.length > 0
            ? decodedToken.full_name
            : undefined,
        is_admin: Boolean(decodedToken.is_admin),
    };
}

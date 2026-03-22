import jwt from "jsonwebtoken";
import type { AppConfig } from "../config";
import type { AuthTokenClaims, PublicUser } from "../types";

export function createAccessToken(user: PublicUser, config: AppConfig): string {
  return jwt.sign(
    {
      email: user.email,
      full_name: user.fullName ?? undefined,
      is_admin: user.isAdmin,
    },
    config.jwtSecret,
    {
      algorithm: "HS256",
      issuer: config.jwtIssuer,
      audience: config.jwtAudience,
      expiresIn: `${config.accessTokenExpireMinutes}m`,
      subject: user.username,
    },
  );
}

export function decodeAccessToken(token: string, config: AppConfig): AuthTokenClaims {
  const decodedToken = jwt.verify(token, config.jwtSecret, {
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
    full_name:
      typeof decodedToken.full_name === "string" && decodedToken.full_name.length > 0
        ? decodedToken.full_name
        : undefined,
    is_admin: Boolean(decodedToken.is_admin),
  };
}

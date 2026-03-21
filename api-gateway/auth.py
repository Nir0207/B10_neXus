from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from schemas import TokenData, User

ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "bionexus-api-gateway")
JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "bionexus-ui")

# Use an environment key when provided; otherwise generate a random process key.
# This avoids a predictable hardcoded secret in source code.
SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(64))
ADMIN_USERNAME: str = os.getenv("GATEWAY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH: str

oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="token")
_ADMIN_PASSWORD_HASH_ENV: str = os.getenv("GATEWAY_ADMIN_PASSWORD_HASH", "")


class JWTError(Exception):
    """Raised when token parsing or validation fails."""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            _, iter_raw, salt, encoded_hash = hashed_password.split("$", maxsplit=3)
            iterations = int(iter_raw)
            expected = base64.urlsafe_b64decode(_pad_base64(encoded_hash))
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            return hmac.compare_digest(candidate, expected)
        except (ValueError, TypeError):
            return False

    return hmac.compare_digest(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 390_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${iterations}${salt}${digest_b64}"


ADMIN_PASSWORD_HASH = _ADMIN_PASSWORD_HASH_ENV or get_password_hash(
    os.getenv("GATEWAY_ADMIN_PASSWORD", "password")
)


def authenticate_user(username: str, password: str) -> bool:
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, ADMIN_PASSWORD_HASH)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode: dict[str, Any] = data.copy()
    now = datetime.now(timezone.utc)
    expire: datetime = now + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = int(expire.timestamp())
    to_encode["iat"] = int(now.timestamp())
    to_encode["nbf"] = int(now.timestamp())
    to_encode["iss"] = JWT_ISSUER
    to_encode["aud"] = JWT_AUDIENCE

    header_segment = _b64url_encode_json({"alg": ALGORITHM, "typ": "JWT"})
    payload_segment = _b64url_encode_json(to_encode)
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_token_subject(token: str) -> str | None:
    try:
        payload = _decode_jwt(token)
        sub: str | None = payload.get("sub") if isinstance(payload, dict) else None
        if not sub:
            return None
        token_data = TokenData(username=sub)
        return token_data.username
    except (JWTError, ValidationError):
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    username: str | None = decode_token_subject(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(username=username, email=f"{username}@bionexus.com")


def _decode_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("Malformed token")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")

    header_raw = _b64url_decode(header_segment)
    try:
        header = json.loads(header_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JWTError("Invalid header") from exc
    if not isinstance(header, dict) or header.get("alg") != ALGORITHM:
        raise JWTError("Invalid algorithm")

    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    provided_signature = _b64url_decode(signature_segment)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise JWTError("Invalid signature")

    payload_raw = _b64url_decode(payload_segment)
    try:
        payload = json.loads(payload_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JWTError("Invalid payload") from exc

    if not isinstance(payload, dict):
        raise JWTError("Invalid payload type")

    exp = payload.get("exp")
    nbf = payload.get("nbf")
    iss = payload.get("iss")
    aud = payload.get("aud")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if exp is not None:
        try:
            exp_ts = int(exp)
        except (TypeError, ValueError) as exc:
            raise JWTError("Invalid expiry") from exc

        if now_ts >= exp_ts:
            raise JWTError("Token expired")
    if nbf is not None:
        try:
            nbf_ts = int(nbf)
        except (TypeError, ValueError) as exc:
            raise JWTError("Invalid not-before") from exc
        if now_ts < nbf_ts:
            raise JWTError("Token not yet valid")
    if iss != JWT_ISSUER:
        raise JWTError("Invalid issuer")
    if aud != JWT_AUDIENCE:
        raise JWTError("Invalid audience")

    return payload


def _b64url_encode_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url_encode(raw)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(_pad_base64(raw))


def _pad_base64(raw: str) -> str:
    return raw + ("=" * ((4 - (len(raw) % 4)) % 4))

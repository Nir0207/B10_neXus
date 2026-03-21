from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from schemas import TokenData, User

ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Use an environment key when provided; otherwise generate a random process key.
# This avoids a predictable hardcoded secret in source code.
SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(64))
ADMIN_USERNAME: str = os.getenv("GATEWAY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH: str

pwd_context: CryptContext = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="token")
ADMIN_PASSWORD_HASH = pwd_context.hash(os.getenv("GATEWAY_ADMIN_PASSWORD", "password"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> bool:
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, ADMIN_PASSWORD_HASH)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token_subject(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
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

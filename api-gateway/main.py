from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from audit import AuditLogMiddleware
from auth import (
    DuplicateUserError,
    InvalidAuthRequestError,
    ReservedUsernameError,
    UserStoreUnavailableError,
    authenticate_user,
    register_user,
)
from database import close_db, init_db
from router import router as api_router
from schemas import Token, UserRegistrationRequest
from settings import get_cors_origins

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "audit.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.audit_log_file = LOG_FILE
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title="BioNexus API Gateway",
    description="GxP Compliant API Gateway Proxying Staging DBs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(AuditLogMiddleware, log_file_path=LOG_FILE)
app.include_router(api_router)


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    try:
        token = await authenticate_user(form_data.username, form_data.password)
    except UserStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@app.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_for_access_token(
    payload: UserRegistrationRequest,
) -> Token:
    try:
        token = await register_user(payload)
    except UserStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ReservedUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidAuthRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return token


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

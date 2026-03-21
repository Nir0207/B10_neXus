from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from audit import AuditLogMiddleware
from auth import authenticate_user, create_access_token
from database import close_db, init_db
from router import router as api_router
from schemas import Token
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token: str = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

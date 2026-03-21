from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from auth import decode_token_subject


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, log_file_path: str) -> None:
        super().__init__(app)
        self.log_file_path = log_file_path

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        timestamp: str = datetime.now(timezone.utc).isoformat()
        endpoint: str = request.url.path
        client_host: str = request.client.host if request.client is not None else "unknown"
        request_hash_input: str = f"{timestamp}:{endpoint}:{request.method}:{client_host}"
        request_hash: str = hashlib.sha256(request_hash_input.encode("utf-8")).hexdigest()

        user_id: str = "anonymous"
        auth_header: str | None = request.headers.get("Authorization")
        if auth_header is not None and auth_header.startswith("Bearer "):
            token: str = auth_header.removeprefix("Bearer ").strip()
            token_sub: str | None = decode_token_subject(token)
            if token_sub is not None:
                user_id = token_sub

        response = await call_next(request)
        log_entry: dict[str, str | int] = {
            "Timestamp": timestamp,
            "User_ID": user_id,
            "Endpoint": endpoint,
            "Request_Hash": request_hash,
            "Status_Code": response.status_code,
        }

        target_path: str = getattr(request.app.state, "audit_log_file", self.log_file_path)
        await run_in_threadpool(self._append_log_entry, target_path, log_entry)
        return response

    @staticmethod
    def _append_log_entry(log_file_path: str, log_entry: dict[str, str | int]) -> None:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(log_entry) + "\n")

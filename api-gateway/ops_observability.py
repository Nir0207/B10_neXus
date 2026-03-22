from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def _gene_context_from_request(request: Request) -> str | None:
    for key in ("id", "gene", "gene_id", "uniprot_id"):
        value = request.path_params.get(key) or request.query_params.get(key)
        if value:
            return str(value)
    return None


class ErrorEventMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        try:
            response = await call_next(request)
        except Exception:
            gene = _gene_context_from_request(request)
            logger.exception(
                "Gateway error event status=500 method=%s path=%s",
                request.method,
                request.url.path,
                extra={"gene_context": gene},
            )
            raise

        if response.status_code >= 400:
            gene = _gene_context_from_request(request)
            logger.error(
                "Gateway error response status=%s method=%s path=%s stacktrace=%s",
                response.status_code,
                request.method,
                request.url.path,
                "".join(traceback.format_stack(limit=25)),
                extra={"gene_context": gene},
            )
        return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        gene = _gene_context_from_request(request)
        logger.error(
            "Gateway error event status=%s method=%s path=%s detail=%s stacktrace=%s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            extra={"gene_context": gene},
        )
        headers = exc.headers or {}
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)

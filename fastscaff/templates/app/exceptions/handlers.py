from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import logger
from app.exceptions.base import AppError
from app.exceptions.codes import (
    ErrForbidden,
    ErrInternal,
    ErrInvalidParams,
    ErrNotFound,
    ErrTooManyRequests,
    ErrUnauthorized,
)


def build_error_body(
    code: int,
    message: str,
    data: Any = None,
) -> Dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def build_error_response(
    exc: AppError,
    *,
    data: Any = None,
) -> JSONResponse:
    """Shared client envelope for AppError (HTTP 200 + business code)."""
    payload_data = data if data is not None else exc.details
    return JSONResponse(
        status_code=200,
        content=build_error_body(exc.code, exc.message, payload_data),
    )


def log_app_error(request: Request, exc: AppError) -> None:
    fields: Dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
        "path": request.url.path,
        "method": request.method,
    }
    if exc.cause is not None:
        logger.error("app error", exc=exc.cause, **fields)
    else:
        logger.warning("app error", **fields)


def _map_http_exception(exc: StarletteHTTPException) -> AppError:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    status = exc.status_code
    if status == 401:
        return ErrUnauthorized.new(detail or ErrUnauthorized.message)
    if status == 403:
        return ErrForbidden.new(detail or ErrForbidden.message)
    if status == 404:
        return ErrNotFound.new(detail or ErrNotFound.message)
    if status == 429:
        return ErrTooManyRequests.new(detail or ErrTooManyRequests.message)
    if 400 <= status < 500:
        return ErrInvalidParams.new(detail or ErrInvalidParams.message)
    return ErrInternal.new(detail or ErrInternal.message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log_app_error(request, exc)
    return build_error_response(exc)


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    logger.warning(
        "validation error",
        path=request.url.path,
        method=request.method,
        errors=errors,
    )
    return JSONResponse(
        status_code=200,
        content=build_error_body(
            ErrInvalidParams.code,
            ErrInvalidParams.message,
            data=errors,
        ),
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    mapped = _map_http_exception(exc)
    if exc.status_code >= 500:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        logger.error(
            "internal error",
            path=request.url.path,
            method=request.method,
            code=ErrInternal.code,
            error=detail,
        )
        return JSONResponse(
            status_code=500,
            content=build_error_body(ErrInternal.code, ErrInternal.message),
        )
    log_app_error(request, mapped)
    return build_error_response(mapped)


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "internal error",
        exc=exc,
        path=request.url.path,
        method=request.method,
    )
    internal = ErrInternal.new()
    return JSONResponse(
        status_code=500,
        content=build_error_body(internal.code, internal.message),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

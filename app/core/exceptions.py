import contextvars
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import logger

# Contextvar to store request id throughout the request lifetime
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="unknown")


class AppException(Exception):
    """Base exception class for all custom application business errors."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(code=code, message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN"):
        super().__init__(code=code, message=message, status_code=403)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(code=code, message=message, status_code=404)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict", code: str = "CONFLICT"):
        super().__init__(code=code, message=message, status_code=409)


class RateLimitException(AppException):
    def __init__(self, message: str = "Too many requests", code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(code=code, message=message, status_code=429)


def format_error_response(code: str, message: str, request_id: str) -> Dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "request_id": request_id
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        req_id = request_id_var.get()
        logger.warning(
            "business_logic_error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            request_id=req_id,
            details=exc.details
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc.code, exc.message, req_id)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = request_id_var.get()
        # Parse Pydantic validation errors nicely
        errors = exc.errors()
        error_messages = []
        for error in errors:
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Invalid value")
            error_messages.append(f"{loc}: {msg}")
        
        message = "; ".join(error_messages) if error_messages else "Request validation failed"
        
        logger.warning(
            "request_validation_error",
            message=message,
            errors=errors,
            request_id=req_id
        )
        
        return JSONResponse(
            status_code=422,
            content=format_error_response("VALIDATION_ERROR", message, req_id)
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = request_id_var.get()
        # Map common Starlette HTTPExceptions to error codes
        code = "HTTP_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
            
        logger.info(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=req_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(code, exc.detail, req_id)
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        req_id = request_id_var.get()
        # Capture raw trace and log it securely, but don't return it
        logger.exception(
            "unhandled_system_error",
            error=str(exc),
            request_id=req_id
        )
        
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                "INTERNAL_SERVER_ERROR",
                "An unexpected internal server error occurred.",
                req_id
            )
        )

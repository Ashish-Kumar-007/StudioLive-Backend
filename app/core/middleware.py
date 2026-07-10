import time
import uuid
import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.exceptions import request_id_var

logger = structlog.get_logger()


class RequestIdLoggingMiddleware:
    """ASGI Middleware that injects Request ID headers and logs HTTP request lifecycles.
    
    Avoids Starlette's BaseHTTPMiddleware loop-conflict issues during async testing.
    """
    
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract X-Request-ID from request headers if present
        request_id = None
        for key, val in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = val.decode("utf-8")
                break
        if not request_id:
            request_id = uuid.uuid4().hex

        # Set request_id in ContextVar and structlog context
        token = request_id_var.set(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                # Inject X-Request-ID response header
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
                
                # Log completion with actual status code
                status_code = message.get("status", 200)
                duration = time.perf_counter() - start_time
                logger.info(
                    "request_completed",
                    method=scope["method"],
                    path=scope["path"],
                    status_code=status_code,
                    duration_ms=round(duration * 1000, 2),
                )
            await send(message)

        # Log request start
        query_params = scope.get("query_string", b"").decode("utf-8")
        logger.info(
            "request_started",
            method=scope["method"],
            path=scope["path"],
            query_params=query_params,
        )

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.exception(
                "request_failed",
                method=scope["method"],
                path=scope["path"],
                duration_ms=round(duration * 1000, 2),
                error=str(e),
            )
            raise
        finally:
            request_id_var.reset(token)

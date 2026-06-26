import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.exceptions import register_exception_handlers, request_id_var
from app.core.logging import setup_logging, logger
from app.db.session import engine

# Initialize structured logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade FastAPI Backend for Photography Studio Quick-Commerce Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request ID and Observability Middleware
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    # Retrieve request ID from header or generate a new one
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    
    # Store request ID in ContextVar for access by handlers and exceptions
    token = request_id_var.set(request_id)
    
    # Bind request_id to structlog context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    start_time = time.perf_counter()
    
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
    )
    
    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        # Inject Request ID header into response
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration * 1000, 2),
            error=str(e),
        )
        # Re-raise the exception, the global handler will intercept it
        raise
    finally:
        # Reset context variables
        request_id_var.reset(token)


# Register unified business and system exception handlers
register_exception_handlers(app)


# Health & Readiness Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness check to confirm API is running."""
    return {"status": "ok", "app_name": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check verifying database connectivity."""
    db_ok = False
    try:
        # Verify database connectivity
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("readiness_db_failed", error=str(e))
    
    if db_ok:
        return {"status": "ready", "database": "connected"}
    
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "database": "disconnected"}
    )

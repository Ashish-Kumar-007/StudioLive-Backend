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


# Request ID and Observability Middleware (ASGI)
from app.core.middleware import RequestIdLoggingMiddleware
app.add_middleware(RequestIdLoggingMiddleware)


# Register unified business and system exception handlers
register_exception_handlers(app)

# Register Domain Routers
from app.modules.auth.router import router as auth_router

app.include_router(auth_router, prefix=settings.API_V1_STR)


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

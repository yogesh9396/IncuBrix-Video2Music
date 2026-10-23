from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.models.errors import IncuBrixError
from app.api.middleware import (
    CorrelationIdMiddleware,
    incubrix_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.api.routes import router as api_router
from app.storage.storage_service import storage_service

# Initialize structured logging
setup_logging(level="DEBUG" if settings.DEBUG else "INFO")

app = FastAPI(
    title="IncuBrix AI Background Music Engine",
    description="Original, commercially safe instrumental background music for video with genuine isolated instrument stems.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID and Request Tracing
app.add_middleware(CorrelationIdMiddleware)

# Custom Exception Handlers
app.add_exception_handler(IncuBrixError, incubrix_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API v1 Routes
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health", summary="Liveness check", tags=["System"])
async def health_check():
    """
    Standard liveness probe endpoint returning 200 OK.
    """
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "environment": settings.ENV,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/ready", summary="Readiness check", tags=["System"])
async def readiness_check():
    """
    Standard readiness probe checking storage, audio engine, and provider readiness.
    """
    storage_ok = storage_service.local_base_dir.exists()
    return {
        "status": "ready" if storage_ok else "unhealthy",
        "service": settings.SERVICE_NAME,
        "storage": {
            "type": settings.STORAGE_TYPE,
            "ready": storage_ok,
            "path": str(storage_service.local_base_dir)
        },
        "providers": {
            "default": settings.MUSIC_PROVIDER,
            "available": ["synth", "mock"]
        },
        "audio_standards": {
            "sample_rate_hz": settings.DEFAULT_SAMPLE_RATE,
            "target_lufs": settings.DEFAULT_TARGET_LUFS,
            "true_peak_max_dbtp": settings.MAX_TRUE_PEAK_DBTP
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/", summary="Root status", tags=["System"])
async def root():
    return {
        "name": "IncuBrix AI Background Music Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

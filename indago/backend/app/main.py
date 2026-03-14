"""
INDAGO Evidence Capture Platform
Main FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("INDAGO Evidence Capture Platform starting...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("INDAGO Evidence Capture Platform shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Professional Digital Evidence Preservation Platform for Forensic Investigators. "
        "Compliant with ISO/IEC 27037, ISO/IEC 27042, RFC 3227, RFC 3161."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api.routes.auth import router as auth_router
from app.api.routes.captures import router as captures_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(captures_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "operational",
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": settings.APP_TAGLINE,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "platform": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )

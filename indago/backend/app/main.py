"""
INDAGO Evidence Capture Platform
Main FastAPI Application - Demo Mode (SQLite, no Celery required)
"""
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.security import get_password_hash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def create_demo_users():
    """Create default users for demo."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            return  # Already exists

        users = [
            User(
                email="admin@indago.local",
                username="admin",
                full_name="INDAGO Administrator",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMINISTRATOR,
                organization="INDAGO Platform",
                is_active=True,
            ),
            User(
                email="investigator@indago.local",
                username="investigator",
                full_name="Demo Investigator",
                hashed_password=get_password_hash("investigator123"),
                role=UserRole.INVESTIGATOR,
                organization="Digital Forensics Unit",
                badge_number="DFU-001",
                is_active=True,
            ),
        ]
        for u in users:
            db.add(u)
        await db.commit()
        logger.info("Demo users created: admin / investigator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info(" INDAGO Evidence Capture Platform")
    logger.info(" Digital Evidence Preservation Platform")
    logger.info("=" * 50)
    await init_db()
    await create_demo_users()
    logger.info("Database ready. Demo users created.")
    logger.info(f"Evidence storage: {settings.EVIDENCE_BASE_PATH}")
    yield
    logger.info("INDAGO shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Professional Digital Evidence Preservation Platform. "
        "Compliant with ISO/IEC 27037, ISO/IEC 27042, RFC 3227, RFC 3161."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes
from app.api.routes.auth import router as auth_router
from app.api.routes.captures import router as captures_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(captures_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health")
async def health_check():
    return {
        "status": "operational",
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": "demo",
        "database": "SQLite (demo)",
        "docs": "/api/docs",
    }


@app.get("/")
async def root():
    return {
        "platform": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/api/health",
    }

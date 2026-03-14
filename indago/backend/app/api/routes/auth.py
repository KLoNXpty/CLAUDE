"""
INDAGO Evidence Capture Platform
Authentication API Routes
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.capture import AuditLog
from app.schemas.capture import LoginRequest, TokenResponse, UserCreateRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and receive JWT token."""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        # Log failed attempt
        audit = AuditLog(
            user_id=user.id if user else 0,
            action="login_failed",
            details={"username": data.username},
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role})

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="login_success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    # Check existing
    result = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=UserRole(data.role),
        organization=data.organization,
        badge_number=data.badge_number,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user

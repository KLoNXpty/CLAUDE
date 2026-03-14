"""
INDAGO Evidence Capture Platform
Pydantic Schemas for API request/response validation
"""
from pydantic import BaseModel, HttpUrl, field_validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class CaptureTypeEnum(str, Enum):
    full_page = "full_page"
    viewport = "viewport"
    social_media = "social_media"
    scheduled = "scheduled"
    profile = "profile"
    thread = "thread"


class CaptureCreateRequest(BaseModel):
    url: str = Field(..., description="Target URL to capture")
    capture_type: CaptureTypeEnum = Field(default=CaptureTypeEnum.full_page)
    case_number: Optional[str] = Field(None, max_length=100)
    case_description: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class CaptureStatusResponse(BaseModel):
    id: int
    evidence_id: UUID
    url: str
    status: str
    progress: float
    capture_type: str
    initiated_at: datetime
    capture_started_at: Optional[datetime]
    capture_completed_at: Optional[datetime]
    error_message: Optional[str]
    celery_task_id: Optional[str]

    class Config:
        from_attributes = True


class CaptureDetailResponse(BaseModel):
    id: int
    evidence_id: UUID
    url: str
    final_url: Optional[str]
    domain: Optional[str]
    status: str
    capture_type: str
    social_platform: Optional[str]
    case_number: Optional[str]
    case_description: Optional[str]
    initiated_at: datetime
    capture_started_at: Optional[datetime]
    capture_completed_at: Optional[datetime]
    server_ip: Optional[str]
    http_status_code: Optional[int]
    user_agent: Optional[str]
    viewport_width: Optional[int]
    viewport_height: Optional[int]
    html_sha256: Optional[str]
    dom_sha256: Optional[str]
    package_sha256: Optional[str]
    package_sha512: Optional[str]
    tsa_timestamp: Optional[str]
    tsa_url: Optional[str]
    total_resources: int
    total_size_bytes: int
    screenshot_count: int
    is_locked: bool
    error_message: Optional[str]

    class Config:
        from_attributes = True


class CaptureListResponse(BaseModel):
    id: int
    evidence_id: UUID
    url: str
    domain: Optional[str]
    status: str
    capture_type: str
    case_number: Optional[str]
    initiated_at: datetime
    capture_completed_at: Optional[datetime]
    total_resources: int
    total_size_bytes: int
    package_sha256: Optional[str]
    is_locked: bool

    class Config:
        from_attributes = True


class ScheduleCreateRequest(BaseModel):
    url: str
    capture_type: CaptureTypeEnum = CaptureTypeEnum.full_page
    schedule_cron: str = Field(..., description="Cron expression (e.g., '0 * * * *' for hourly)")
    schedule_description: Optional[str] = None
    case_number: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class CompareRequest(BaseModel):
    capture_id_a: int
    capture_id_b: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    username: str
    full_name: str
    password: str
    role: str = "investigator"
    organization: Optional[str] = None
    badge_number: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    organization: Optional[str]
    badge_number: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

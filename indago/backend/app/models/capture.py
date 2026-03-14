"""
INDAGO Evidence Capture Platform
Evidence Capture Models - Core forensic data structures
Compliant with ISO/IEC 27037, RFC 3227
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, JSON,
    ForeignKey, Enum as SAEnum, BigInteger, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from app.core.database import Base


class CaptureStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CaptureType(str, enum.Enum):
    FULL_PAGE = "full_page"
    VIEWPORT = "viewport"
    SOCIAL_MEDIA = "social_media"
    SCHEDULED = "scheduled"
    PROFILE = "profile"
    THREAD = "thread"


class SocialPlatform(str, enum.Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    GENERIC = "generic"


class EvidenceCapture(Base):
    """
    Main evidence capture record.
    Each capture represents a forensic collection event with full chain of custody.
    """
    __tablename__ = "evidence_captures"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True
    )

    # Target
    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=True, index=True)
    capture_type = Column(SAEnum(CaptureType), default=CaptureType.FULL_PAGE, nullable=False)
    social_platform = Column(SAEnum(SocialPlatform), nullable=True)

    # Status
    status = Column(SAEnum(CaptureStatus), default=CaptureStatus.PENDING, nullable=False, index=True)
    celery_task_id = Column(String(255), nullable=True)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    # Timestamps (forensic)
    initiated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    capture_started_at = Column(DateTime(timezone=True), nullable=True)
    capture_completed_at = Column(DateTime(timezone=True), nullable=True)
    first_byte_at = Column(DateTime(timezone=True), nullable=True)

    # Network metadata
    server_ip = Column(String(45), nullable=True)
    server_headers = Column(JSON, nullable=True)
    http_status_code = Column(Integer, nullable=True)
    tls_info = Column(JSON, nullable=True)
    dns_info = Column(JSON, nullable=True)
    whois_info = Column(JSON, nullable=True)
    final_url = Column(Text, nullable=True)  # After redirects
    redirect_chain = Column(JSON, nullable=True)

    # Browser context
    user_agent = Column(Text, nullable=True)
    viewport_width = Column(Integer, nullable=True)
    viewport_height = Column(Integer, nullable=True)
    browser_version = Column(String(100), nullable=True)

    # Evidence hashes (primary integrity markers)
    html_sha256 = Column(String(64), nullable=True)
    dom_sha256 = Column(String(64), nullable=True)
    package_sha256 = Column(String(64), nullable=True)
    package_sha512 = Column(String(128), nullable=True)

    # Storage paths
    storage_path = Column(String(500), nullable=True)
    s3_bucket = Column(String(255), nullable=True)
    s3_key = Column(String(500), nullable=True)

    # Chain of custody
    investigator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    investigator_ip = Column(String(45), nullable=True)
    case_number = Column(String(100), nullable=True, index=True)
    case_description = Column(Text, nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)  # Read-only after capture

    # Timestamps
    tsa_timestamp = Column(Text, nullable=True)  # RFC 3161 timestamp token (base64)
    tsa_url = Column(String(500), nullable=True)
    blockchain_anchor = Column(String(255), nullable=True)

    # Options used
    capture_options = Column(JSON, nullable=True)

    # Statistics
    total_resources = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    screenshot_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    investigator = relationship("User", back_populates="captures")
    screenshots = relationship("Screenshot", back_populates="capture", cascade="all, delete-orphan")
    resources = relationship("CapturedResource", back_populates="capture", cascade="all, delete-orphan")
    forensic_logs = relationship("ForensicLog", back_populates="capture", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="capture")
    metadata_record = relationship("EvidenceMetadata", back_populates="capture", uselist=False)
    social_data = relationship("SocialMediaData", back_populates="capture", uselist=False)
    scheduled_captures = relationship("ScheduledCapture", back_populates="parent_capture")
    report = relationship("EvidenceReport", back_populates="capture", uselist=False)

    def __repr__(self):
        return f"<EvidenceCapture {self.evidence_id} - {self.url}>"


class Screenshot(Base):
    """
    Individual screenshot files with forensic metadata.
    PNG uncompressed format per forensic standards.
    """
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), nullable=False)
    screenshot_type = Column(String(50), nullable=False)  # full_page, viewport, element
    filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=True)
    s3_key = Column(String(500), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=False)
    sha512 = Column(String(128), nullable=True)
    md5 = Column(String(32), nullable=True)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)
    user_agent = Column(Text, nullable=True)
    viewport_width = Column(Integer, nullable=True)
    viewport_height = Column(Integer, nullable=True)
    element_selector = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture = relationship("EvidenceCapture", back_populates="screenshots")


class CapturedResource(Base):
    """
    Individual captured resources (HTML, CSS, JS, images, videos, etc.)
    """
    __tablename__ = "captured_resources"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), nullable=False)
    resource_url = Column(Text, nullable=False)
    resource_type = Column(String(100), nullable=False)  # html, css, js, image, video, font, etc.
    filename = Column(String(500), nullable=True)
    storage_path = Column(String(1000), nullable=True)
    s3_key = Column(String(500), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(200), nullable=True)
    http_status = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    sha512 = Column(String(128), nullable=True)
    md5 = Column(String(32), nullable=True)
    headers = Column(JSON, nullable=True)
    downloaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture = relationship("EvidenceCapture", back_populates="resources")


class EvidenceMetadata(Base):
    """
    Complete forensic metadata record for an evidence capture.
    """
    __tablename__ = "evidence_metadata"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), unique=True, nullable=False)
    page_title = Column(Text, nullable=True)
    page_description = Column(Text, nullable=True)
    canonical_url = Column(Text, nullable=True)
    page_language = Column(String(20), nullable=True)
    cookies = Column(JSON, nullable=True)
    local_storage = Column(JSON, nullable=True)
    session_storage = Column(JSON, nullable=True)
    meta_tags = Column(JSON, nullable=True)
    open_graph = Column(JSON, nullable=True)
    structured_data = Column(JSON, nullable=True)
    links_found = Column(JSON, nullable=True)
    iframes_found = Column(JSON, nullable=True)
    total_comments = Column(Integer, default=0)
    page_load_time_ms = Column(Integer, nullable=True)
    network_requests = Column(JSON, nullable=True)
    performance_timing = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture = relationship("EvidenceCapture", back_populates="metadata_record")


class SocialMediaData(Base):
    """
    Social media specific captured data.
    """
    __tablename__ = "social_media_data"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), unique=True, nullable=False)
    platform = Column(SAEnum(SocialPlatform), nullable=False)
    post_id = Column(String(255), nullable=True)
    author_username = Column(String(255), nullable=True)
    author_display_name = Column(String(255), nullable=True)
    author_profile_url = Column(Text, nullable=True)
    author_verified = Column(Boolean, nullable=True)
    post_text = Column(Text, nullable=True)
    post_datetime = Column(DateTime(timezone=True), nullable=True)
    hashtags = Column(JSON, nullable=True)
    mentions = Column(JSON, nullable=True)
    likes_count = Column(BigInteger, nullable=True)
    shares_count = Column(BigInteger, nullable=True)
    comments_count = Column(BigInteger, nullable=True)
    views_count = Column(BigInteger, nullable=True)
    comments_data = Column(JSON, nullable=True)  # Full comments structure
    media_urls = Column(JSON, nullable=True)
    is_deleted = Column(Boolean, default=False)
    is_story = Column(Boolean, default=False)
    is_live = Column(Boolean, default=False)
    raw_api_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture = relationship("EvidenceCapture", back_populates="social_data")


class ForensicLog(Base):
    """
    Forensic process log - Every action during capture is recorded.
    Compliant with RFC 3227.
    """
    __tablename__ = "forensic_logs"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)
    sequence = Column(Integer, nullable=False)  # Order of operations
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture = relationship("EvidenceCapture", back_populates="forensic_logs")


class AuditLog(Base):
    """
    Chain of custody audit trail.
    Records every access, download, and transfer of evidence.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")
    capture = relationship("EvidenceCapture", back_populates="audit_logs")


class ScheduledCapture(Base):
    """
    Scheduled recurring evidence captures.
    """
    __tablename__ = "scheduled_captures"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    capture_type = Column(SAEnum(CaptureType), default=CaptureType.FULL_PAGE)
    schedule_cron = Column(String(100), nullable=False)
    schedule_description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    investigator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_number = Column(String(100), nullable=True)
    parent_capture_id = Column(Integer, ForeignKey("evidence_captures.id"), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0)
    capture_options = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    parent_capture = relationship("EvidenceCapture", back_populates="scheduled_captures")


class EvidenceReport(Base):
    """
    Generated evidence report (PDF/JSON).
    """
    __tablename__ = "evidence_reports"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("evidence_captures.id"), unique=True, nullable=False)
    pdf_path = Column(String(1000), nullable=True)
    pdf_s3_key = Column(String(500), nullable=True)
    json_path = Column(String(1000), nullable=True)
    json_s3_key = Column(String(500), nullable=True)
    pdf_sha256 = Column(String(64), nullable=True)
    json_sha256 = Column(String(64), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    template_version = Column(String(50), default="1.0")

    capture = relationship("EvidenceCapture", back_populates="report")

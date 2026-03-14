"""
INDAGO Evidence Capture Platform
User Model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    INVESTIGATOR = "investigator"
    ADMINISTRATOR = "administrator"
    AUDITOR = "auditor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.INVESTIGATOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    organization = Column(String(255), nullable=True)
    badge_number = Column(String(100), nullable=True)  # For law enforcement / forensic investigators
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    captures = relationship("EvidenceCapture", back_populates="investigator")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

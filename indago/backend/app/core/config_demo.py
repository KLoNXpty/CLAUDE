"""
INDAGO - Demo configuration using SQLite (no external services required)
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/indago_demo.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:////tmp/indago_demo.db")
os.environ.setdefault("SECRET_KEY", "indago-demo-secret-key-2024-change-in-production")
os.environ.setdefault("EVIDENCE_BASE_PATH", "/tmp/indago_evidence")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("S3_ENDPOINT_URL", "")
os.environ.setdefault("DEBUG", "true")

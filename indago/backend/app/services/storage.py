"""
INDAGO Evidence Capture Platform
Storage Service - S3-compatible Object Storage
"""
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage for evidence packages."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    def ensure_buckets(self):
        """Create required buckets if they don't exist."""
        for bucket in [settings.S3_BUCKET_EVIDENCE, settings.S3_BUCKET_REPORTS]:
            try:
                self.client.head_bucket(Bucket=bucket)
            except ClientError:
                self.client.create_bucket(Bucket=bucket)
                logger.info(f"Created bucket: {bucket}")

    def upload_file(self, local_path: str, bucket: str, s3_key: str) -> bool:
        """Upload a file to S3 storage."""
        try:
            self.client.upload_file(local_path, bucket, s3_key)
            return True
        except Exception as e:
            logger.error(f"Upload failed {local_path} -> s3://{bucket}/{s3_key}: {e}")
            return False

    def upload_evidence_directory(self, evidence_dir: Path, evidence_id: str) -> dict:
        """Upload entire evidence directory to S3."""
        uploaded = {}
        for file_path in evidence_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(evidence_dir.parent)
                s3_key = f"evidence/{evidence_id}/{rel_path}"
                success = self.upload_file(
                    str(file_path),
                    settings.S3_BUCKET_EVIDENCE,
                    s3_key,
                )
                if success:
                    uploaded[str(rel_path)] = s3_key
        return uploaded

    def generate_presigned_url(self, bucket: str, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for evidence download."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return ""

    def download_file(self, bucket: str, s3_key: str, local_path: str) -> bool:
        """Download a file from S3 storage."""
        try:
            self.client.download_file(bucket, s3_key, local_path)
            return True
        except Exception as e:
            logger.error(f"Download failed s3://{bucket}/{s3_key}: {e}")
            return False

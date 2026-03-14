"""
INDAGO Evidence Capture Platform
Celery Task Workers - Async Forensic Capture Pipeline
"""
import asyncio
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

from celery import Task
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.capture import (
    EvidenceCapture, Screenshot, CapturedResource,
    EvidenceMetadata, SocialMediaData, ForensicLog,
    CaptureStatus, EvidenceReport
)
from app.forensics.hasher import generate_hash_manifest, compute_hash_from_file
from app.forensics.logger import CaptureForensicLogger, ForensicEvent
from app.forensics.timestamp import RFC3161Timestamper
from app.capture.engine import ForensicCaptureEngine
from app.capture.social import SocialMediaExtractor, detect_platform
from app.capture.warc import WARCBuilder
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="capture.execute_forensic_capture",
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def execute_forensic_capture(self: Task, capture_id: int) -> dict:
    """
    Main forensic capture task.
    Executes complete evidence collection pipeline.
    """
    return run_async(_execute_capture_async(self, capture_id))


async def _execute_capture_async(task: Task, capture_id: int) -> dict:
    """Async implementation of forensic capture pipeline."""
    async with AsyncSessionLocal() as db:
        # Fetch capture record
        result = await db.execute(
            select(EvidenceCapture).where(EvidenceCapture.id == capture_id)
        )
        capture = result.scalar_one_or_none()
        if not capture:
            raise ValueError(f"Capture {capture_id} not found")

        evidence_id = str(capture.evidence_id)
        url = capture.url

        # Setup directories
        evidence_dir = Path(settings.EVIDENCE_BASE_PATH) / evidence_id
        dirs = {
            "screenshots": evidence_dir / "screenshots",
            "html": evidence_dir / "html",
            "resources": evidence_dir / "resources",
            "video_capture": evidence_dir / "video_capture",
            "metadata": evidence_dir / "metadata",
            "logs": evidence_dir / "logs",
            "hashes": evidence_dir / "hashes",
            "warc_archive": evidence_dir / "warc_archive",
            "report": evidence_dir / "report",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        # Initialize forensic logger
        forensic_logger = CaptureForensicLogger(
            evidence_id=evidence_id,
            investigator_id=capture.investigator_id,
            investigator_ip=capture.investigator_ip or "unknown",
        )

        # Update status
        capture.status = CaptureStatus.RUNNING
        capture.capture_started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # ================================================================
            # STEP 1: DNS + Network Pre-capture
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "dns_lookup", "progress": 5})

            engine = ForensicCaptureEngine(evidence_id, evidence_dir, forensic_logger)
            forensic_logger.log_capture_start(url, capture.investigator_ip or "unknown")

            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            capture.domain = domain

            dns_info = await engine.resolve_dns(domain)
            capture.dns_info = dns_info

            # TLS
            if url.startswith("https://"):
                tls_info = await engine.get_tls_info(domain)
                capture.tls_info = tls_info

            # WHOIS
            whois_info = await engine.get_whois_info(domain)
            capture.whois_info = whois_info

            await db.commit()

            # ================================================================
            # STEP 2: Browser Initialization & Navigation
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "browser_launch", "progress": 10})

            await engine.initialize()
            nav_result = await engine.navigate_and_capture(url)

            capture.server_ip = dns_info.get("ips", [None])[0]
            capture.server_headers = nav_result.get("response_headers", {})
            capture.http_status_code = nav_result.get("http_status")
            capture.final_url = nav_result.get("final_url")
            capture.user_agent = settings.USER_AGENT
            capture.viewport_width = settings.VIEWPORT_WIDTH
            capture.viewport_height = settings.VIEWPORT_HEIGHT
            await db.commit()

            # ================================================================
            # STEP 3: Page Interaction (Scroll + Expand)
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "page_interaction", "progress": 20})

            await engine.scroll_page()
            await engine.expand_comments()

            # ================================================================
            # STEP 4: Screenshots
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "screenshots", "progress": 30})

            screenshot_results = await engine.capture_screenshots()
            screenshot_count = 0
            for ss in screenshot_results:
                screenshot_record = Screenshot(
                    capture_id=capture_id,
                    screenshot_type=ss["type"],
                    filename=ss["filename"],
                    storage_path=ss["path"],
                    sha256=ss["sha256"],
                    sha512=ss["sha512"],
                    md5=ss["md5"],
                    file_size_bytes=ss["file_size"],
                    timestamp_utc=datetime.fromisoformat(ss["timestamp_utc"]),
                    user_agent=settings.USER_AGENT,
                    viewport_width=settings.VIEWPORT_WIDTH,
                    viewport_height=settings.VIEWPORT_HEIGHT,
                )
                db.add(screenshot_record)
                screenshot_count += 1

            capture.screenshot_count = screenshot_count
            await db.commit()

            # ================================================================
            # STEP 5: HTML Capture
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "html_capture", "progress": 40})

            html_result = await engine.capture_html()
            capture.html_sha256 = html_result["original_html"]["sha256"]
            capture.dom_sha256 = html_result["rendered_dom"]["sha256"]
            await db.commit()

            # ================================================================
            # STEP 6: Resource Download
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "resource_download", "progress": 50})

            resources = await engine.download_resources(url)
            total_size = 0
            for res in resources:
                resource_record = CapturedResource(
                    capture_id=capture_id,
                    resource_url=res["url"],
                    resource_type=res["resource_type"],
                    filename=res["filename"],
                    storage_path=res["path"],
                    file_size_bytes=res["file_size"],
                    mime_type=res["mime_type"],
                    http_status=res["http_status"],
                    sha256=res["sha256"],
                    sha512=res["sha512"],
                    md5=res["md5"],
                    headers=res["headers"],
                    downloaded_at=datetime.now(timezone.utc),
                )
                db.add(resource_record)
                total_size += res["file_size"]

            capture.total_resources = len(resources)
            capture.total_size_bytes = total_size
            await db.commit()

            # ================================================================
            # STEP 7: Metadata Extraction
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "metadata", "progress": 60})

            metadata = await engine.extract_metadata()
            metadata_record = EvidenceMetadata(
                capture_id=capture_id,
                page_title=metadata.get("title"),
                page_language=metadata.get("language"),
                cookies=metadata.get("cookies"),
                meta_tags=metadata.get("meta_tags"),
                open_graph=metadata.get("open_graph"),
                iframes_found=metadata.get("iframes"),
                links_found=metadata.get("links"),
                network_requests=engine.network_requests[:500],
            )
            db.add(metadata_record)

            # ================================================================
            # STEP 8: Social Media Extraction (if applicable)
            # ================================================================
            platform = detect_platform(url)
            if platform != "generic":
                social_extractor = SocialMediaExtractor(engine.page, forensic_logger)
                social_data = await social_extractor.extract(url)
                social_record = SocialMediaData(
                    capture_id=capture_id,
                    platform=platform,
                    post_text=social_data.get("post_text"),
                    author_username=social_data.get("author_username"),
                    author_display_name=social_data.get("author_display_name"),
                    post_datetime=social_data.get("post_datetime"),
                    hashtags=social_data.get("hashtags"),
                    comments_data=social_data.get("comments"),
                    media_urls=social_data.get("images"),
                )
                db.add(social_record)

            await db.commit()

            # ================================================================
            # STEP 9: Video Recording
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "video_save", "progress": 65})

            video_path = await engine.stop_recording()
            await engine.close()

            # ================================================================
            # STEP 10: WARC Archive
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "warc_creation", "progress": 70})

            warc_path = await _create_warc_archive(url, evidence_dir, metadata, resources)
            if warc_path:
                forensic_logger.log(
                    ForensicEvent.WARC_CREATED,
                    f"WARC archive created: {warc_path}",
                    data={"path": str(warc_path)},
                )

            # ================================================================
            # STEP 11: Hash Manifest
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "hashing", "progress": 80})

            from app.models.user import User
            user_result = await db.execute(select(User).where(User.id == capture.investigator_id))
            investigator = user_result.scalar_one()

            hash_manifest = generate_hash_manifest(
                directory=evidence_dir,
                evidence_id=evidence_id,
                investigator=investigator.full_name,
                capture_timestamp=capture.capture_started_at.isoformat(),
            )

            manifest_path = dirs["hashes"] / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(hash_manifest, f, indent=2, ensure_ascii=False)

            package_hash = hash_manifest["package_integrity"]
            capture.package_sha256 = package_hash["sha256"]
            capture.package_sha512 = package_hash["sha512"]

            forensic_logger.log(
                ForensicEvent.HASH_MANIFEST_CREATED,
                f"Hash manifest created: {len(hash_manifest['files'])} files",
                data={"package_sha256": package_hash["sha256"], "total_files": package_hash["total_files"]},
            )

            # ================================================================
            # STEP 12: RFC 3161 Timestamp
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "timestamp", "progress": 85})

            timestamper = RFC3161Timestamper(settings.TSA_URL)
            timestamp_result = timestamper.request_timestamp(
                package_hash["sha256"].encode("utf-8")
            )
            if timestamp_result:
                capture.tsa_timestamp = timestamp_result.get("timestamp_token_b64")
                capture.tsa_url = settings.TSA_URL
                forensic_logger.log_timestamp(settings.TSA_URL, True)

                tsa_path = dirs["metadata"] / "tsa_timestamp.json"
                with open(tsa_path, "w") as f:
                    json.dump(timestamp_result, f, indent=2)

            # ================================================================
            # STEP 13: Save Forensic Log
            # ================================================================
            task.update_state(state="PROGRESS", meta={"step": "finalizing", "progress": 90})

            forensic_logger.log(
                ForensicEvent.EVIDENCE_PACK_CREATED,
                f"Evidence package complete: {evidence_id}",
                data={"evidence_id": evidence_id, "total_resources": len(resources)},
            )

            # Save log to file
            log_path = dirs["logs"] / "forensic_log.json"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(forensic_logger.to_json_log())

            # Save log entries to DB
            for i, entry in enumerate(forensic_logger.get_entries()):
                log_record = ForensicLog(
                    capture_id=capture_id,
                    event_type=entry.event_type,
                    event_data=entry.data,
                    message=entry.message,
                    sequence=entry.sequence,
                    timestamp_utc=datetime.fromisoformat(entry.timestamp_utc),
                    success=entry.success,
                )
                db.add(log_record)

            # ================================================================
            # STEP 14: Finalize
            # ================================================================
            capture.status = CaptureStatus.COMPLETED
            capture.capture_completed_at = datetime.now(timezone.utc)
            capture.is_locked = True
            capture.storage_path = str(evidence_dir)
            await db.commit()

            return {
                "evidence_id": evidence_id,
                "status": "completed",
                "screenshots": screenshot_count,
                "resources": len(resources),
                "package_sha256": package_hash["sha256"],
            }

        except Exception as e:
            logger.error(f"Capture {capture_id} failed: {e}", exc_info=True)
            forensic_logger.log(
                ForensicEvent.CAPTURE_FAILED,
                f"Capture failed: {str(e)}",
                data={"error": str(e)},
                success=False,
            )

            capture.status = CaptureStatus.FAILED
            capture.error_message = str(e)
            await db.commit()

            try:
                await engine.close()
            except Exception:
                pass

            raise


async def _create_warc_archive(url: str, evidence_dir: Path, metadata: dict, resources: list) -> Optional[Path]:
    """Create WARC archive from captured data."""
    try:
        warc_dir = evidence_dir / "warc_archive"
        warc_dir.mkdir(exist_ok=True)
        warc_path = warc_dir / "archive"

        builder = WARCBuilder(warc_path, url)
        builder.start()

        # Add HTML
        html_path = evidence_dir / "html" / "rendered_dom.html"
        if html_path.exists():
            with open(html_path, "rb") as f:
                html_content = f.read()
            builder.add_response(url, 200, {"Content-Type": "text/html; charset=utf-8"}, html_content)

        # Add metadata
        builder.add_metadata(url, metadata)

        # Add resources
        for res in resources[:50]:  # First 50 resources
            res_path = res.get("path")
            if res_path and Path(res_path).exists():
                with open(res_path, "rb") as f:
                    content = f.read()
                builder.add_resource(res["url"], res.get("mime_type", "application/octet-stream"), content)

        return builder.save()
    except Exception as e:
        logger.warning(f"WARC creation failed: {e}")
        return None


@celery_app.task(name="capture.generate_report")
def generate_evidence_report(capture_id: int) -> dict:
    """Generate PDF and JSON evidence report."""
    return run_async(_generate_report_async(capture_id))


async def _generate_report_async(capture_id: int) -> dict:
    """Async report generation."""
    from app.reports.generator import ReportGenerator

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EvidenceCapture).where(EvidenceCapture.id == capture_id)
        )
        capture = result.scalar_one_or_none()
        if not capture:
            raise ValueError(f"Capture {capture_id} not found")

        generator = ReportGenerator(capture, db)
        report_paths = await generator.generate()

        report_record = EvidenceReport(
            capture_id=capture_id,
            pdf_path=report_paths.get("pdf"),
            json_path=report_paths.get("json"),
            pdf_sha256=report_paths.get("pdf_sha256"),
            json_sha256=report_paths.get("json_sha256"),
        )
        db.add(report_record)
        await db.commit()

        return report_paths

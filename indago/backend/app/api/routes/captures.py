"""
INDAGO Evidence Capture Platform
Capture API Routes - Demo mode (inline async tasks, no Celery)
"""
import asyncio
import zipfile
import io
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.capture import (
    EvidenceCapture, CaptureStatus, Screenshot, CapturedResource,
    ForensicLog, EvidenceMetadata, SocialMediaData, AuditLog,
    ScheduledCapture
)
from app.schemas.capture import (
    CaptureCreateRequest, CaptureStatusResponse, CaptureDetailResponse,
    CaptureListResponse, ScheduleCreateRequest, CompareRequest
)
from app.forensics.hasher import verify_hash_manifest
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/captures", tags=["Evidence Captures"])


@router.post("", response_model=CaptureStatusResponse, status_code=202)
async def create_capture(
    request: Request,
    data: CaptureCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate a new forensic evidence capture."""
    capture = EvidenceCapture(
        url=str(data.url),
        capture_type=data.capture_type,
        investigator_id=current_user.id,
        investigator_ip=request.client.host if request.client else "127.0.0.1",
        case_number=data.case_number,
        case_description=data.case_description,
        capture_options=data.options,
        status=CaptureStatus.PENDING,
        progress=0.0,
    )
    db.add(capture)
    await db.commit()
    await db.refresh(capture)

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        capture_id=capture.id,
        action="capture_created",
        details={"url": capture.url},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    await db.commit()

    # Run capture in background
    background_tasks.add_task(_run_capture_background, capture.id)

    return capture


async def _run_capture_background(capture_id: int):
    """Run the forensic capture pipeline in background."""
    from app.core.database import AsyncSessionLocal
    from app.capture.pipeline import run_forensic_pipeline

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(EvidenceCapture).where(EvidenceCapture.id == capture_id))
        capture = result.scalar_one_or_none()
        if capture:
            await run_forensic_pipeline(capture_id, db)


@router.get("", response_model=list[CaptureListResponse])
async def list_captures(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    case_number: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(EvidenceCapture)
    if current_user.role not in [UserRole.ADMINISTRATOR]:
        query = query.where(EvidenceCapture.investigator_id == current_user.id)
    if status:
        query = query.where(EvidenceCapture.status == status)
    if case_number:
        query = query.where(EvidenceCapture.case_number == case_number)
    query = query.order_by(desc(EvidenceCapture.initiated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{capture_id}", response_model=CaptureDetailResponse)
async def get_capture(
    capture_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    audit = AuditLog(
        user_id=current_user.id,
        capture_id=capture_id,
        action="evidence_accessed",
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()
    return capture


@router.get("/{capture_id}/status", response_model=CaptureStatusResponse)
async def get_capture_status(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_capture_or_404(capture_id, db, current_user)


@router.get("/{capture_id}/screenshots")
async def get_screenshots(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_capture_or_404(capture_id, db, current_user)
    result = await db.execute(select(Screenshot).where(Screenshot.capture_id == capture_id))
    return [
        {
            "id": ss.id,
            "type": ss.screenshot_type,
            "filename": ss.filename,
            "sha256": ss.sha256,
            "file_size_bytes": ss.file_size_bytes,
            "timestamp_utc": ss.timestamp_utc.isoformat() if ss.timestamp_utc else None,
        }
        for ss in result.scalars().all()
    ]


@router.get("/{capture_id}/logs")
async def get_forensic_logs(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_capture_or_404(capture_id, db, current_user)
    result = await db.execute(
        select(ForensicLog).where(ForensicLog.capture_id == capture_id).order_by(ForensicLog.sequence)
    )
    return [
        {
            "sequence": log.sequence,
            "event_type": log.event_type,
            "message": log.message,
            "timestamp_utc": log.timestamp_utc.isoformat() if log.timestamp_utc else None,
            "success": log.success,
            "data": log.event_data,
        }
        for log in result.scalars().all()
    ]


@router.get("/{capture_id}/metadata")
async def get_metadata(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_capture_or_404(capture_id, db, current_user)
    result = await db.execute(select(EvidenceMetadata).where(EvidenceMetadata.capture_id == capture_id))
    meta = result.scalar_one_or_none()
    if not meta:
        return {}
    return {
        "title": meta.page_title,
        "description": meta.page_description,
        "language": meta.page_language,
        "cookies": meta.cookies,
        "meta_tags": meta.meta_tags,
        "open_graph": meta.open_graph,
        "links_found": meta.links_found,
        "iframes_found": meta.iframes_found,
    }


@router.get("/{capture_id}/social")
async def get_social_data(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_capture_or_404(capture_id, db, current_user)
    result = await db.execute(select(SocialMediaData).where(SocialMediaData.capture_id == capture_id))
    social = result.scalar_one_or_none()
    if not social:
        return {"message": "No social media data for this capture"}
    return {
        "platform": social.platform,
        "author_username": social.author_username,
        "author_display_name": social.author_display_name,
        "post_text": social.post_text,
        "post_datetime": social.post_datetime.isoformat() if social.post_datetime else None,
        "hashtags": social.hashtags,
        "likes_count": social.likes_count,
        "comments_count": social.comments_count,
        "comments_data": social.comments_data,
        "media_urls": social.media_urls,
    }


@router.get("/{capture_id}/hashes")
async def get_hashes(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    res_result = await db.execute(select(CapturedResource).where(CapturedResource.capture_id == capture_id))
    ss_result = await db.execute(select(Screenshot).where(Screenshot.capture_id == capture_id))
    return {
        "evidence_id": str(capture.evidence_id),
        "package": {"sha256": capture.package_sha256, "sha512": capture.package_sha512},
        "html": {"sha256": capture.html_sha256},
        "dom": {"sha256": capture.dom_sha256},
        "screenshots": [
            {"filename": ss.filename, "sha256": ss.sha256, "sha512": ss.sha512, "md5": ss.md5}
            for ss in ss_result.scalars().all()
        ],
        "resources": [
            {"url": r.resource_url, "sha256": r.sha256, "type": r.resource_type}
            for r in res_result.scalars().all()[:50]
        ],
    }


@router.post("/{capture_id}/verify")
async def verify_integrity(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    if not capture.storage_path:
        raise HTTPException(status_code=400, detail="Evidence storage path not available")

    evidence_dir = Path(capture.storage_path)
    manifest_path = evidence_dir / "hashes" / "manifest.json"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Hash manifest not found")

    with open(manifest_path) as f:
        manifest = json.load(f)

    verification = verify_hash_manifest(manifest, evidence_dir)
    return {
        "evidence_id": str(capture.evidence_id),
        "verified": verification["verified"],
        "total_files": len(manifest.get("files", {})),
        "errors": verification.get("errors", []),
        "package_sha256": manifest.get("package_integrity", {}).get("sha256"),
        "stored_sha256": capture.package_sha256,
        "hashes_match": manifest.get("package_integrity", {}).get("sha256") == capture.package_sha256,
    }


@router.post("/{capture_id}/report")
async def generate_report(
    capture_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    if capture.status != CaptureStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Capture must be completed first")
    background_tasks.add_task(_generate_report_bg, capture_id)
    return {"status": "generating", "capture_id": capture_id}


async def _generate_report_bg(capture_id: int):
    from app.core.database import AsyncSessionLocal
    from app.reports.generator import ReportGenerator
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(EvidenceCapture).where(EvidenceCapture.id == capture_id))
        capture = result.scalar_one_or_none()
        if capture:
            generator = ReportGenerator(capture, db)
            await generator.generate()


@router.get("/{capture_id}/download")
async def download_evidence(
    capture_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    if capture.status != CaptureStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Capture not yet completed")
    if not capture.storage_path:
        raise HTTPException(status_code=404, detail="Evidence files not found")

    evidence_dir = Path(capture.storage_path)
    if not evidence_dir.exists():
        raise HTTPException(status_code=404, detail="Evidence directory not found")

    audit = AuditLog(
        user_id=current_user.id,
        capture_id=capture_id,
        action="evidence_downloaded",
        details={"evidence_id": str(capture.evidence_id)},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in evidence_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(evidence_dir.parent)
                zf.write(file_path, arcname)
    buffer.seek(0)
    zip_data = buffer.read()
    evidence_id = str(capture.evidence_id)

    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="evidence_{evidence_id[:8]}.zip"',
            "Content-Length": str(len(zip_data)),
        },
    )


@router.post("/{capture_id}/cancel")
async def cancel_capture(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await _get_capture_or_404(capture_id, db, current_user)
    if capture.status not in [CaptureStatus.PENDING, CaptureStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="Cannot cancel in current state")
    capture.status = CaptureStatus.CANCELLED
    await db.commit()
    return {"status": "cancelled", "capture_id": capture_id}


@router.post("/compare")
async def compare_captures(
    data: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture_a = await _get_capture_or_404(data.capture_id_a, db, current_user)
    capture_b = await _get_capture_or_404(data.capture_id_b, db, current_user)

    differences = {
        "capture_a": {"id": data.capture_id_a, "url": capture_a.url},
        "capture_b": {"id": data.capture_id_b, "url": capture_b.url},
        "changes": [],
        "identical": True,
    }
    checks = [
        ("html_sha256", "HTML changed"),
        ("dom_sha256", "DOM changed"),
        ("http_status_code", "HTTP status changed"),
        ("server_ip", "Server IP changed"),
        ("total_resources", "Resource count changed"),
    ]
    for field, label in checks:
        a_val = getattr(capture_a, field)
        b_val = getattr(capture_b, field)
        if a_val != b_val:
            differences["changes"].append({"type": label, "value_a": a_val, "value_b": b_val})

    differences["identical"] = len(differences["changes"]) == 0
    differences["total_changes"] = len(differences["changes"])
    return differences


@router.post("/schedules", status_code=201)
async def create_scheduled_capture(
    data: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from croniter import croniter
    try:
        cron = croniter(data.schedule_cron)
        next_run = cron.get_next(datetime)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    schedule = ScheduledCapture(
        url=str(data.url),
        capture_type=data.capture_type,
        schedule_cron=data.schedule_cron,
        schedule_description=data.schedule_description,
        investigator_id=current_user.id,
        case_number=data.case_number,
        next_run_at=next_run,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return {
        "id": schedule.id,
        "url": schedule.url,
        "schedule_cron": schedule.schedule_cron,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "is_active": schedule.is_active,
    }


@router.get("/schedules/list")
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScheduledCapture).where(ScheduledCapture.investigator_id == current_user.id)
    )
    return [
        {
            "id": s.id,
            "url": s.url,
            "schedule_cron": s.schedule_cron,
            "is_active": s.is_active,
            "run_count": s.run_count,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        }
        for s in result.scalars().all()
    ]


async def _get_capture_or_404(capture_id, db, current_user):
    result = await db.execute(select(EvidenceCapture).where(EvidenceCapture.id == capture_id))
    capture = result.scalar_one_or_none()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")
    if current_user.role == UserRole.INVESTIGATOR and capture.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return capture

"""
INDAGO Evidence Capture Platform
Inline Capture Pipeline - Runs directly without Celery
"""
import asyncio
import json
import hashlib
import socket
import ssl
import time
import aiohttp
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.capture import (
    EvidenceCapture, Screenshot, CapturedResource,
    EvidenceMetadata, SocialMediaData, ForensicLog,
    CaptureStatus
)
from app.forensics.hasher import compute_hash_from_bytes, compute_hash_from_file, generate_hash_manifest
from app.forensics.logger import CaptureForensicLogger, ForensicEvent
from app.forensics.timestamp import RFC3161Timestamper

logger = logging.getLogger(__name__)


async def run_forensic_pipeline(capture_id: int, db: AsyncSession):
    """
    Run the complete forensic capture pipeline inline.
    No Celery required - runs as an async background task.
    """
    result = await db.execute(select(EvidenceCapture).where(EvidenceCapture.id == capture_id))
    capture = result.scalar_one_or_none()
    if not capture:
        return

    evidence_id = str(capture.evidence_id)
    url = capture.url

    # Create directory structure
    evidence_dir = Path(settings.EVIDENCE_BASE_PATH) / evidence_id
    dirs = {
        "screenshots": evidence_dir / "screenshots",
        "html": evidence_dir / "html",
        "resources": evidence_dir / "resources",
        "metadata": evidence_dir / "metadata",
        "logs": evidence_dir / "logs",
        "hashes": evidence_dir / "hashes",
        "warc_archive": evidence_dir / "warc_archive",
        "report": evidence_dir / "report",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    forensic_logger = CaptureForensicLogger(
        evidence_id=evidence_id,
        investigator_id=capture.investigator_id,
        investigator_ip=capture.investigator_ip or "127.0.0.1",
    )

    # Update status
    capture.status = CaptureStatus.RUNNING
    capture.capture_started_at = datetime.now(timezone.utc)
    capture.progress = 5.0
    await db.commit()

    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        capture.domain = domain

        forensic_logger.log_capture_start(url, capture.investigator_ip or "127.0.0.1")

        # ── STEP 1: DNS Resolution ────────────────────────────────────────
        dns_info = await _resolve_dns(domain, forensic_logger)
        capture.dns_info = dns_info
        capture.server_ip = dns_info.get("ips", [None])[0]
        capture.progress = 15.0
        await db.commit()

        # ── STEP 2: TLS Info ──────────────────────────────────────────────
        if url.startswith("https://"):
            tls_info = await _get_tls_info(domain, forensic_logger)
            capture.tls_info = tls_info
        capture.progress = 20.0
        await db.commit()

        # ── STEP 3: HTTP Request + HTML Capture ───────────────────────────
        http_result = await _fetch_page(url, forensic_logger, dirs["html"])
        capture.http_status_code = http_result.get("status")
        capture.server_headers = http_result.get("headers", {})
        capture.final_url = http_result.get("final_url", url)
        capture.html_sha256 = http_result.get("html_sha256")
        capture.dom_sha256 = http_result.get("html_sha256")  # same in non-browser mode
        capture.user_agent = settings.USER_AGENT
        capture.viewport_width = settings.VIEWPORT_WIDTH
        capture.viewport_height = settings.VIEWPORT_HEIGHT
        capture.progress = 35.0
        await db.commit()

        # ── STEP 4: Playwright Screenshot (if available) ──────────────────
        screenshots = await _try_playwright_capture(url, evidence_dir, dirs, forensic_logger)
        screenshot_count = 0
        for ss in screenshots:
            ss_record = Screenshot(
                capture_id=capture_id,
                screenshot_type=ss["type"],
                filename=ss["filename"],
                storage_path=ss["path"],
                sha256=ss["sha256"],
                sha512=ss.get("sha512", ""),
                md5=ss.get("md5", ""),
                file_size_bytes=ss.get("file_size", 0),
                timestamp_utc=datetime.now(timezone.utc),
                user_agent=settings.USER_AGENT,
                viewport_width=settings.VIEWPORT_WIDTH,
                viewport_height=settings.VIEWPORT_HEIGHT,
            )
            db.add(ss_record)
            screenshot_count += 1
        capture.screenshot_count = screenshot_count
        capture.progress = 55.0
        await db.commit()

        # ── STEP 5: Resource Download ─────────────────────────────────────
        resources = await _download_resources(url, http_result.get("html", ""), dirs["resources"], forensic_logger)
        total_size = 0
        for res in resources:
            res_record = CapturedResource(
                capture_id=capture_id,
                resource_url=res["url"],
                resource_type=res["type"],
                filename=res["filename"],
                storage_path=res["path"],
                file_size_bytes=res["size"],
                mime_type=res["mime"],
                http_status=res["status"],
                sha256=res["sha256"],
                downloaded_at=datetime.now(timezone.utc),
            )
            db.add(res_record)
            total_size += res["size"]
        capture.total_resources = len(resources)
        capture.total_size_bytes = total_size
        capture.progress = 65.0
        await db.commit()

        # ── STEP 6: Metadata ──────────────────────────────────────────────
        metadata = _extract_metadata_from_html(http_result.get("html", ""), url)
        meta_record = EvidenceMetadata(
            capture_id=capture_id,
            page_title=metadata.get("title"),
            page_language=metadata.get("language"),
            cookies=[],
            meta_tags=metadata.get("meta_tags"),
            open_graph=metadata.get("og"),
            links_found=metadata.get("links"),
            network_requests=[],
        )
        db.add(meta_record)
        forensic_logger.log(ForensicEvent.METADATA_EXTRACTED, f"Title: {metadata.get('title', 'N/A')}")

        # ── STEP 7: Hash Manifest ─────────────────────────────────────────
        capture.progress = 75.0
        await db.commit()

        user_result = await db.execute(
            select(EvidenceCapture).where(EvidenceCapture.id == capture_id)
        )
        from app.models.user import User
        u_result = await db.execute(select(User).where(User.id == capture.investigator_id))
        investigator = u_result.scalar_one()

        hash_manifest = generate_hash_manifest(
            directory=evidence_dir,
            evidence_id=evidence_id,
            investigator=investigator.full_name,
            capture_timestamp=capture.capture_started_at.isoformat(),
        )
        manifest_path = dirs["hashes"] / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(hash_manifest, f, indent=2)

        pkg = hash_manifest["package_integrity"]
        capture.package_sha256 = pkg["sha256"]
        capture.package_sha512 = pkg["sha512"]
        forensic_logger.log(ForensicEvent.HASH_MANIFEST_CREATED, f"Package SHA-256: {pkg['sha256'][:16]}...")
        capture.progress = 85.0
        await db.commit()

        # ── STEP 8: RFC 3161 Timestamp ────────────────────────────────────
        try:
            timestamper = RFC3161Timestamper(settings.TSA_URL)
            ts_result = timestamper.request_timestamp(pkg["sha256"].encode())
            if ts_result:
                capture.tsa_timestamp = ts_result.get("timestamp_token_b64", "")[:200]
                capture.tsa_url = settings.TSA_URL
                forensic_logger.log_timestamp(settings.TSA_URL, True)
                tsa_path = dirs["metadata"] / "tsa_timestamp.json"
                with open(tsa_path, "w") as f:
                    json.dump(ts_result, f, indent=2)
        except Exception as e:
            logger.warning(f"TSA timestamp failed (non-critical): {e}")
            forensic_logger.log_timestamp(settings.TSA_URL, False)

        capture.progress = 90.0
        await db.commit()

        # ── STEP 9: Save forensic log ─────────────────────────────────────
        forensic_logger.log(ForensicEvent.EVIDENCE_PACK_CREATED, f"Evidence package complete: {evidence_id}")
        log_path = dirs["logs"] / "forensic_log.json"
        with open(log_path, "w") as f:
            f.write(forensic_logger.to_json_log())

        for entry in forensic_logger.get_entries():
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

        # ── STEP 10: Finalize ─────────────────────────────────────────────
        capture.status = CaptureStatus.COMPLETED
        capture.capture_completed_at = datetime.now(timezone.utc)
        capture.is_locked = True
        capture.storage_path = str(evidence_dir)
        capture.progress = 100.0
        await db.commit()

        logger.info(f"Capture {evidence_id[:8]} completed successfully")

    except Exception as e:
        logger.error(f"Capture {capture_id} failed: {e}", exc_info=True)
        forensic_logger.log(ForensicEvent.CAPTURE_FAILED, f"Failed: {e}", success=False)
        capture.status = CaptureStatus.FAILED
        capture.error_message = str(e)
        await db.commit()


async def _resolve_dns(domain: str, fl: CaptureForensicLogger) -> dict:
    """Simple DNS resolution."""
    start = time.time()
    ips = []
    try:
        import socket
        info = socket.getaddrinfo(domain, None)
        ips = list(set(r[4][0] for r in info))
    except Exception as e:
        fl.log(ForensicEvent.DNS_RESULT, f"DNS failed: {e}", success=False)
        return {"domain": domain, "ips": [], "error": str(e)}

    duration_ms = int((time.time() - start) * 1000)
    fl.log_dns(domain, ips, duration_ms)
    return {"domain": domain, "ips": ips, "records": {"A": ips}}


async def _get_tls_info(domain: str, fl: CaptureForensicLogger) -> dict:
    """Extract TLS certificate info."""
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.create_connection((domain, 443), timeout=10), server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            tls_info = {
                "subject": dict(x[0] for x in cert.get("subject", [])),
                "issuer": dict(x[0] for x in cert.get("issuer", [])),
                "not_before": cert.get("notBefore"),
                "not_after": cert.get("notAfter"),
                "protocol": ssock.version(),
            }
            fl.log_tls(domain, tls_info)
            return tls_info
    except Exception as e:
        return {"error": str(e)}


async def _fetch_page(url: str, fl: CaptureForensicLogger, html_dir: Path) -> dict:
    """Fetch page HTML with aiohttp."""
    fl.log(ForensicEvent.HTTP_REQUEST, f"GET {url}")
    result = {"status": 0, "headers": {}, "html": "", "final_url": url}

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.USER_AGENT},
            timeout=timeout,
        ) as session:
            async with session.get(url, allow_redirects=True) as resp:
                result["status"] = resp.status
                result["headers"] = dict(resp.headers)
                result["final_url"] = str(resp.url)
                html = await resp.text(errors="replace")
                result["html"] = html

                # Save HTML
                html_path = html_dir / "original.html"
                async with aiofiles.open(str(html_path), "w", encoding="utf-8") as f:
                    await f.write(html)

                html_hash = compute_hash_from_bytes(html.encode("utf-8"))
                result["html_sha256"] = html_hash.sha256
                fl.log_hash("original.html", html_hash.sha256, html_hash.sha512, html_hash.file_size)
                fl.log_http_response(str(resp.url), resp.status, dict(resp.headers), len(html))

    except Exception as e:
        fl.log(ForensicEvent.HTTP_RESPONSE, f"Fetch failed: {e}", success=False)
        result["error"] = str(e)

    return result


async def _try_playwright_capture(url: str, evidence_dir: Path, dirs: dict, fl: CaptureForensicLogger) -> list:
    """Try to take screenshots with Playwright. Gracefully skip if not available."""
    screenshots = []
    try:
        from playwright.async_api import async_playwright
        fl.log(ForensicEvent.BROWSER_LAUNCH, "Launching Chromium for screenshot")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
                user_agent=settings.USER_AGENT,
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=settings.PAGE_LOAD_TIMEOUT_MS)
                await asyncio.sleep(2)

                # Full page
                full_path = dirs["screenshots"] / "full_page.png"
                await page.screenshot(path=str(full_path), full_page=True, type="png")
                h = compute_hash_from_file(full_path)
                fl.log_screenshot("full_page", "full_page.png", h.sha256, (settings.VIEWPORT_WIDTH, 1080))
                screenshots.append({"type": "full_page", "filename": "full_page.png",
                                     "path": str(full_path), "sha256": h.sha256,
                                     "sha512": h.sha512, "md5": h.md5, "file_size": h.file_size})

                # Viewport
                vp_path = dirs["screenshots"] / "viewport.png"
                await page.screenshot(path=str(vp_path), full_page=False, type="png")
                vh = compute_hash_from_file(vp_path)
                screenshots.append({"type": "viewport", "filename": "viewport.png",
                                     "path": str(vp_path), "sha256": vh.sha256,
                                     "sha512": vh.sha512, "md5": vh.md5, "file_size": vh.file_size})

            except Exception as e:
                fl.log(ForensicEvent.SCREENSHOT_TAKEN, f"Screenshot failed: {e}", success=False)
            finally:
                await browser.close()

    except ImportError:
        fl.log(ForensicEvent.BROWSER_LAUNCH, "Playwright not available - skipping screenshots", success=False)
    except Exception as e:
        fl.log(ForensicEvent.BROWSER_LAUNCH, f"Browser error: {e}", success=False)

    return screenshots


async def _download_resources(url: str, html: str, resources_dir: Path, fl: CaptureForensicLogger) -> list:
    """Extract and download linked resources from HTML."""
    import re
    resources = []

    # Extract resource URLs from HTML
    patterns = [
        (r'<link[^>]+href=["\']([^"\']+)["\']', "stylesheet"),
        (r'<script[^>]+src=["\']([^"\']+)["\']', "script"),
        (r'<img[^>]+src=["\']([^"\']+)["\']', "image"),
    ]

    base_url = url.rstrip("/")
    found_urls = set()

    for pattern, res_type in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches[:20]:  # Limit per type
            if match.startswith("http"):
                found_urls.add((match, res_type))
            elif match.startswith("/"):
                parsed = urlparse(url)
                found_urls.add((f"{parsed.scheme}://{parsed.netloc}{match}", res_type))

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(
        headers={"User-Agent": settings.USER_AGENT},
        timeout=timeout
    ) as session:
        for i, (res_url, res_type) in enumerate(list(found_urls)[:30]):
            try:
                async with session.get(res_url) as resp:
                    content = await resp.read()
                    mime = resp.headers.get("content-type", "application/octet-stream").split(";")[0]
                    ext = _mime_to_ext(mime)
                    filename = f"resource_{i:04d}{ext}"
                    file_path = resources_dir / filename
                    async with aiofiles.open(str(file_path), "wb") as f:
                        await f.write(content)
                    h = compute_hash_from_bytes(content)
                    resources.append({
                        "url": res_url, "type": res_type, "filename": filename,
                        "path": str(file_path), "mime": mime, "status": resp.status,
                        "size": len(content), "sha256": h.sha256,
                    })
                    fl.log(ForensicEvent.RESOURCE_DOWNLOAD, f"Downloaded {res_type}: {res_url[:60]}")
            except Exception:
                pass

    return resources


def _extract_metadata_from_html(html: str, url: str) -> dict:
    """Extract metadata from HTML using regex."""
    import re
    metadata = {"url": url, "meta_tags": {}, "og": {}, "links": []}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    metadata["title"] = title_match.group(1).strip() if title_match else None

    lang_match = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
    metadata["language"] = lang_match.group(1) if lang_match else None

    for m in re.finditer(r'<meta\s+(?:name|property)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE):
        key, val = m.group(1), m.group(2)
        if key.startswith("og:"):
            metadata["og"][key] = val
        else:
            metadata["meta_tags"][key] = val

    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    metadata["links"] = [l for l in links if l.startswith("http")][:100]

    return metadata


def _mime_to_ext(mime: str) -> str:
    exts = {
        "text/css": ".css", "application/javascript": ".js", "text/javascript": ".js",
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "image/webp": ".webp", "image/svg+xml": ".svg", "video/mp4": ".mp4",
        "text/html": ".html", "application/json": ".json",
    }
    return exts.get(mime, ".bin")

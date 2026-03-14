"""
INDAGO Evidence Capture Platform
Forensic Web Capture Engine - Playwright Chromium Headless
Implements ISO/IEC 27037 evidence collection procedures
"""
import asyncio
import json
import ssl
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import aiohttp
import aiofiles
import dns.resolver
import whois
import logging

from app.core.config import settings
from app.forensics.logger import CaptureForensicLogger, ForensicEvent
from app.forensics.hasher import compute_hash_from_bytes, compute_hash_from_file

logger = logging.getLogger(__name__)


class ForensicCaptureEngine:
    """
    Core capture engine using Playwright Chromium in headless mode.
    Every action is logged for forensic chain of custody.
    Compliant with ISO/IEC 27037 evidence collection procedures.
    """

    def __init__(self, evidence_id: str, output_dir: Path, forensic_logger: CaptureForensicLogger):
        self.evidence_id = evidence_id
        self.output_dir = output_dir
        self.forensic_logger = forensic_logger
        self.browser = None
        self.context = None
        self.page = None
        self.network_requests = []
        self.network_responses = []

    async def initialize(self):
        """Launch Playwright browser with forensic configuration."""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.BROWSER_HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        self.context = await self.browser.new_context(
            viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
            user_agent=settings.USER_AGENT,
            locale="en-US",
            timezone_id="UTC",
            accept_downloads=True,
            ignore_https_errors=False,
            record_video_dir=str(self.output_dir / "video_capture"),
            record_video_size={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
        )

        self.page = await self.context.new_page()

        # Intercept all network requests for forensic logging
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)

        self.forensic_logger.log(
            ForensicEvent.BROWSER_LAUNCH,
            f"Chromium launched - User-Agent: {settings.USER_AGENT}",
            data={
                "user_agent": settings.USER_AGENT,
                "viewport": f"{settings.VIEWPORT_WIDTH}x{settings.VIEWPORT_HEIGHT}",
                "headless": settings.BROWSER_HEADLESS,
            },
        )

    def _on_request(self, request):
        self.network_requests.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "resource_type": request.resource_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_response(self, response):
        self.network_responses.append({
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def resolve_dns(self, domain: str) -> dict:
        """Perform DNS resolution and record results forensically."""
        start = time.time()
        dns_info = {"domain": domain, "records": {}, "ips": []}

        try:
            resolver = dns.resolver.Resolver()
            for record_type in ["A", "AAAA", "MX", "NS", "TXT"]:
                try:
                    answers = resolver.resolve(domain, record_type)
                    dns_info["records"][record_type] = [str(r) for r in answers]
                    if record_type == "A":
                        dns_info["ips"] = [str(r) for r in answers]
                except Exception:
                    pass
        except Exception as e:
            dns_info["error"] = str(e)

        duration_ms = int((time.time() - start) * 1000)
        self.forensic_logger.log_dns(domain, dns_info.get("ips", []), duration_ms)
        return dns_info

    async def get_tls_info(self, domain: str, port: int = 443) -> dict:
        """Extract TLS certificate information for forensic record."""
        tls_info = {"domain": domain, "port": port}
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.create_connection((domain, port), timeout=10), server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                tls_info.update({
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "version": cert.get("version"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "serial_number": cert.get("serialNumber"),
                    "san": cert.get("subjectAltName", []),
                    "protocol": ssock.version(),
                    "cipher": ssock.cipher(),
                })
                self.forensic_logger.log_tls(domain, tls_info)
        except Exception as e:
            tls_info["error"] = str(e)
            logger.warning(f"TLS info collection failed for {domain}: {e}")
        return tls_info

    async def get_whois_info(self, domain: str) -> dict:
        """Retrieve WHOIS information for the domain."""
        try:
            w = whois.whois(domain)
            whois_data = {
                "domain_name": str(w.domain_name) if w.domain_name else None,
                "registrar": str(w.registrar) if w.registrar else None,
                "creation_date": str(w.creation_date) if w.creation_date else None,
                "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                "updated_date": str(w.updated_date) if w.updated_date else None,
                "name_servers": list(w.name_servers) if w.name_servers else [],
                "status": list(w.status) if w.status else [],
                "emails": list(w.emails) if w.emails else [],
                "org": str(w.org) if w.org else None,
                "country": str(w.country) if w.country else None,
            }
            self.forensic_logger.log(
                ForensicEvent.WHOIS_LOOKUP,
                f"WHOIS data retrieved for {domain}",
                data=whois_data,
            )
            return whois_data
        except Exception as e:
            logger.warning(f"WHOIS failed for {domain}: {e}")
            return {"error": str(e)}

    async def navigate_and_capture(self, url: str) -> dict:
        """
        Main forensic capture procedure.
        Navigate to URL and capture all content.
        """
        capture_start = datetime.now(timezone.utc)

        self.forensic_logger.log(
            ForensicEvent.PAGE_NAVIGATE,
            f"Navigating to: {url}",
            data={"url": url, "timestamp_utc": capture_start.isoformat()},
        )

        # Navigate with full resource loading
        try:
            response = await self.page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.PAGE_LOAD_TIMEOUT_MS,
            )
        except Exception:
            # Fallback: wait for domcontentloaded
            response = await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.PAGE_LOAD_TIMEOUT_MS,
            )

        load_time_ms = int((datetime.now(timezone.utc) - capture_start).total_seconds() * 1000)

        http_status = response.status if response else 0
        response_headers = dict(response.headers) if response else {}
        final_url = self.page.url

        self.forensic_logger.log_http_response(
            final_url,
            http_status,
            response_headers,
            len(await response.body()) if response else 0,
        )

        self.forensic_logger.log(
            ForensicEvent.PAGE_LOAD_COMPLETE,
            f"Page loaded in {load_time_ms}ms - HTTP {http_status}",
            data={
                "load_time_ms": load_time_ms,
                "http_status": http_status,
                "final_url": final_url,
                "original_url": url,
            },
        )

        return {
            "http_status": http_status,
            "response_headers": response_headers,
            "final_url": final_url,
            "load_time_ms": load_time_ms,
            "capture_timestamp_utc": capture_start.isoformat(),
        }

    async def capture_screenshots(self) -> list[dict]:
        """
        Capture forensic screenshots.
        PNG uncompressed for maximum forensic fidelity.
        """
        screenshots_dir = self.output_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        results = []
        timestamp_utc = datetime.now(timezone.utc)

        # Full page screenshot
        full_path = screenshots_dir / "full_page.png"
        await self.page.screenshot(
            path=str(full_path),
            full_page=True,
            type="png",
        )
        full_hash = compute_hash_from_file(full_path)
        self.forensic_logger.log_screenshot(
            "full_page",
            "full_page.png",
            full_hash.sha256,
            (settings.VIEWPORT_WIDTH, await self._get_page_height()),
        )
        results.append({
            "type": "full_page",
            "filename": "full_page.png",
            "path": str(full_path),
            "sha256": full_hash.sha256,
            "sha512": full_hash.sha512,
            "md5": full_hash.md5,
            "file_size": full_hash.file_size,
            "timestamp_utc": timestamp_utc.isoformat(),
        })

        # Viewport screenshot
        viewport_path = screenshots_dir / "viewport.png"
        await self.page.screenshot(
            path=str(viewport_path),
            full_page=False,
            type="png",
        )
        viewport_hash = compute_hash_from_file(viewport_path)
        self.forensic_logger.log_screenshot(
            "viewport",
            "viewport.png",
            viewport_hash.sha256,
            (settings.VIEWPORT_WIDTH, settings.VIEWPORT_HEIGHT),
        )
        results.append({
            "type": "viewport",
            "filename": "viewport.png",
            "path": str(viewport_path),
            "sha256": viewport_hash.sha256,
            "sha512": viewport_hash.sha512,
            "md5": viewport_hash.md5,
            "file_size": viewport_hash.file_size,
            "timestamp_utc": timestamp_utc.isoformat(),
        })

        return results

    async def _get_page_height(self) -> int:
        """Get total page height."""
        try:
            return await self.page.evaluate("document.documentElement.scrollHeight")
        except Exception:
            return settings.VIEWPORT_HEIGHT

    async def scroll_page(self):
        """
        Scroll through the entire page to trigger lazy loading.
        Records scroll actions in forensic log.
        """
        self.forensic_logger.log(ForensicEvent.SCROLL_START, "Beginning forensic page scroll")

        total_height = await self._get_page_height()
        viewport_height = settings.VIEWPORT_HEIGHT
        current_position = 0

        while current_position < total_height:
            current_position = min(current_position + viewport_height, total_height)
            await self.page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(settings.SCROLL_DELAY_MS / 1000)
            # Update height in case new content loaded
            total_height = await self._get_page_height()

        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        self.forensic_logger.log(ForensicEvent.SCROLL_COMPLETE, f"Scroll complete - Total height: {total_height}px")

    async def capture_html(self) -> dict:
        """Capture original HTML and rendered DOM."""
        html_dir = self.output_dir / "html"
        html_dir.mkdir(exist_ok=True)

        # Original HTML (server response)
        try:
            original_html_bytes = await self.page.evaluate(
                "document.documentElement.outerHTML"
            )
            original_html = original_html_bytes if isinstance(original_html_bytes, str) else ""
        except Exception:
            original_html = ""

        # Rendered DOM (after JavaScript execution)
        rendered_dom = await self.page.content()

        # Save both
        orig_path = html_dir / "original.html"
        dom_path = html_dir / "rendered_dom.html"

        async with aiofiles.open(str(orig_path), "w", encoding="utf-8") as f:
            await f.write(original_html)

        async with aiofiles.open(str(dom_path), "w", encoding="utf-8") as f:
            await f.write(rendered_dom)

        orig_hash = compute_hash_from_file(orig_path)
        dom_hash = compute_hash_from_file(dom_path)

        self.forensic_logger.log_hash("original.html", orig_hash.sha256, orig_hash.sha512, orig_hash.file_size)
        self.forensic_logger.log_hash("rendered_dom.html", dom_hash.sha256, dom_hash.sha512, dom_hash.file_size)

        return {
            "original_html": {"path": str(orig_path), "sha256": orig_hash.sha256, "size": orig_hash.file_size},
            "rendered_dom": {"path": str(dom_path), "sha256": dom_hash.sha256, "size": dom_hash.file_size},
        }

    async def extract_metadata(self) -> dict:
        """Extract comprehensive page metadata."""
        metadata = {}

        try:
            metadata = await self.page.evaluate("""
                () => {
                    const getMeta = (name) => {
                        const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                        return el ? el.getAttribute('content') : null;
                    };

                    const metas = {};
                    document.querySelectorAll('meta').forEach(m => {
                        const key = m.getAttribute('name') || m.getAttribute('property');
                        if (key) metas[key] = m.getAttribute('content');
                    });

                    const og = {};
                    document.querySelectorAll('meta[property^="og:"]').forEach(m => {
                        og[m.getAttribute('property')] = m.getAttribute('content');
                    });

                    const iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({
                        src: f.src,
                        id: f.id,
                        width: f.width,
                        height: f.height,
                    }));

                    const links = Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter((v, i, arr) => arr.indexOf(v) === i)
                        .slice(0, 500);

                    return {
                        title: document.title,
                        canonical: document.querySelector('link[rel="canonical"]')?.href,
                        language: document.documentElement.lang,
                        charset: document.characterSet,
                        meta_tags: metas,
                        open_graph: og,
                        iframe_count: iframes.length,
                        iframes: iframes,
                        link_count: links.length,
                        links: links,
                        last_modified: document.lastModified,
                        scripts_count: document.querySelectorAll('script').length,
                        stylesheets_count: document.querySelectorAll('link[rel="stylesheet"]').length,
                        images_count: document.querySelectorAll('img').length,
                        videos_count: document.querySelectorAll('video').length,
                    };
                }
            """)
        except Exception as e:
            metadata["error"] = str(e)

        # Get cookies
        try:
            cookies = await self.context.cookies()
            metadata["cookies"] = cookies
        except Exception:
            metadata["cookies"] = []

        self.forensic_logger.log(
            ForensicEvent.METADATA_EXTRACTED,
            f"Metadata extracted: {metadata.get('title', 'N/A')}",
            data={"title": metadata.get("title"), "language": metadata.get("language")},
        )

        return metadata

    async def download_resources(self, url: str) -> list[dict]:
        """Download all page resources for complete evidence package."""
        resources_dir = self.output_dir / "resources"
        resources_dir.mkdir(exist_ok=True)
        downloaded = []

        # Get all resource URLs from page
        resource_urls = await self.page.evaluate("""
            () => {
                const urls = new Set();
                // Scripts
                document.querySelectorAll('script[src]').forEach(s => urls.add(s.src));
                // Stylesheets
                document.querySelectorAll('link[rel="stylesheet"]').forEach(l => urls.add(l.href));
                // Images
                document.querySelectorAll('img[src]').forEach(i => urls.add(i.src));
                // Videos
                document.querySelectorAll('video source, video[src]').forEach(v => urls.add(v.src || v.currentSrc));
                // Fonts
                document.querySelectorAll('link[as="font"]').forEach(f => urls.add(f.href));
                return Array.from(urls).filter(u => u && u.startsWith('http'));
            }
        """)

        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.USER_AGENT}
        ) as session:
            for i, resource_url in enumerate(resource_urls[:200]):  # Limit to 200 resources
                try:
                    async with session.get(resource_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        content = await resp.read()
                        mime_type = resp.headers.get("content-type", "application/octet-stream")

                        # Determine file extension
                        ext = self._get_extension(mime_type, resource_url)
                        filename = f"resource_{i:04d}{ext}"
                        file_path = resources_dir / filename

                        async with aiofiles.open(str(file_path), "wb") as f:
                            await f.write(content)

                        file_hash = compute_hash_from_bytes(content)
                        resource_type = self._get_resource_type(mime_type)

                        downloaded.append({
                            "url": resource_url,
                            "filename": filename,
                            "path": str(file_path),
                            "mime_type": mime_type,
                            "resource_type": resource_type,
                            "http_status": resp.status,
                            "file_size": len(content),
                            "sha256": file_hash.sha256,
                            "sha512": file_hash.sha512,
                            "md5": file_hash.md5,
                            "headers": dict(resp.headers),
                        })

                        self.forensic_logger.log(
                            ForensicEvent.RESOURCE_DOWNLOAD,
                            f"Downloaded {resource_type}: {resource_url[:80]}",
                            data={"url": resource_url, "sha256": file_hash.sha256, "size": len(content)},
                        )
                except Exception as e:
                    self.forensic_logger.log(
                        ForensicEvent.RESOURCE_DOWNLOAD_FAILED,
                        f"Failed to download: {resource_url[:80]}",
                        data={"url": resource_url, "error": str(e)},
                        success=False,
                    )

        return downloaded

    def _get_extension(self, mime_type: str, url: str) -> str:
        """Determine file extension from MIME type."""
        extensions = {
            "text/html": ".html",
            "text/css": ".css",
            "application/javascript": ".js",
            "text/javascript": ".js",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "application/json": ".json",
            "font/woff2": ".woff2",
            "font/woff": ".woff",
        }
        base_mime = mime_type.split(";")[0].strip()
        return extensions.get(base_mime, ".bin")

    def _get_resource_type(self, mime_type: str) -> str:
        """Classify resource type from MIME."""
        if "javascript" in mime_type:
            return "script"
        if "css" in mime_type:
            return "stylesheet"
        if "image" in mime_type:
            return "image"
        if "video" in mime_type:
            return "video"
        if "audio" in mime_type:
            return "audio"
        if "font" in mime_type:
            return "font"
        if "html" in mime_type:
            return "html"
        return "other"

    async def expand_comments(self) -> int:
        """
        Attempt to expand comment sections (social media, news sites).
        Returns number of comment expand actions performed.
        """
        self.forensic_logger.log(ForensicEvent.COMMENTS_EXPAND, "Attempting to expand comments")
        expanded = 0

        # Common "load more comments" patterns
        expand_selectors = [
            '[data-testid="tweet-replies"]',
            '.comment-load-more',
            '[aria-label*="comment"]',
            'button:has-text("View more replies")',
            'button:has-text("Load more comments")',
            'button:has-text("Show more")',
            '.Comments__loadMore',
            '.js-comments-load-more',
        ]

        for selector in expand_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements[:10]:  # Max 10 per selector
                    try:
                        await element.click()
                        await asyncio.sleep(1)
                        expanded += 1
                    except Exception:
                        pass
            except Exception:
                pass

        self.forensic_logger.log(
            ForensicEvent.COMMENTS_EXPAND,
            f"Comment expansion complete - {expanded} actions",
            data={"expanded_count": expanded},
        )
        return expanded

    async def stop_recording(self) -> Optional[str]:
        """Stop video recording and return path."""
        if self.context:
            try:
                video = await self.page.video
                if video:
                    video_path = await video.path()
                    video_hash = compute_hash_from_file(video_path)
                    self.forensic_logger.log(
                        ForensicEvent.VIDEO_RECORDING_STOP,
                        f"Video recording saved: {video_path}",
                        data={"path": video_path, "sha256": video_hash.sha256},
                    )
                    return video_path
            except Exception as e:
                logger.warning(f"Video recording retrieval failed: {e}")
        return None

    async def close(self):
        """Clean up browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()

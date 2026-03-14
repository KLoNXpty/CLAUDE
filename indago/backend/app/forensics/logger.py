"""
INDAGO Evidence Capture Platform
Forensic Logger - Complete audit trail per RFC 3227
Every action during capture is logged with timestamp and sequence number.
"""
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


class ForensicEvent(str, Enum):
    # Process lifecycle
    CAPTURE_INITIATED = "capture_initiated"
    CAPTURE_START = "capture_start"
    CAPTURE_COMPLETE = "capture_complete"
    CAPTURE_FAILED = "capture_failed"
    CAPTURE_CANCELLED = "capture_cancelled"

    # Network
    DNS_LOOKUP = "dns_lookup"
    DNS_RESULT = "dns_result"
    TLS_HANDSHAKE = "tls_handshake"
    TLS_CERTIFICATE = "tls_certificate"
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    REDIRECT_FOLLOWED = "redirect_followed"

    # Browser
    BROWSER_LAUNCH = "browser_launch"
    PAGE_NAVIGATE = "page_navigate"
    PAGE_LOAD_START = "page_load_start"
    PAGE_LOAD_COMPLETE = "page_load_complete"
    PAGE_RENDER = "page_render"
    SCROLL_START = "scroll_start"
    SCROLL_COMPLETE = "scroll_complete"
    COMMENTS_EXPAND = "comments_expand"
    IFRAME_DETECTED = "iframe_detected"
    DYNAMIC_CONTENT = "dynamic_content"

    # Capture actions
    SCREENSHOT_TAKEN = "screenshot_taken"
    VIDEO_RECORDING_START = "video_recording_start"
    VIDEO_RECORDING_STOP = "video_recording_stop"
    RESOURCE_DOWNLOAD = "resource_download"
    RESOURCE_DOWNLOAD_FAILED = "resource_download_failed"
    WARC_CREATED = "warc_created"

    # Metadata
    METADATA_EXTRACTED = "metadata_extracted"
    WHOIS_LOOKUP = "whois_lookup"
    SOCIAL_DATA_EXTRACTED = "social_data_extracted"

    # Integrity
    HASH_CALCULATED = "hash_calculated"
    HASH_MANIFEST_CREATED = "hash_manifest_created"
    TIMESTAMP_REQUESTED = "timestamp_requested"
    TIMESTAMP_RECEIVED = "timestamp_received"
    EVIDENCE_SIGNED = "evidence_signed"

    # Package
    EVIDENCE_PACK_CREATED = "evidence_pack_created"
    REPORT_GENERATED = "report_generated"
    EVIDENCE_LOCKED = "evidence_locked"
    EVIDENCE_UPLOADED = "evidence_uploaded"

    # Access
    EVIDENCE_ACCESSED = "evidence_accessed"
    EVIDENCE_DOWNLOADED = "evidence_downloaded"
    EVIDENCE_TRANSFERRED = "evidence_transferred"


@dataclass
class ForensicLogEntry:
    evidence_id: str
    event_type: str
    sequence: int
    timestamp_utc: str
    investigator_id: Optional[int] = None
    investigator_ip: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None
    duration_ms: Optional[int] = None
    success: bool = True

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class CaptureForensicLogger:
    """
    In-memory forensic logger for a single capture session.
    All events are sequenced and timestamped.
    """

    def __init__(
        self,
        evidence_id: str,
        investigator_id: Optional[int] = None,
        investigator_ip: Optional[str] = None,
    ):
        self.evidence_id = evidence_id
        self.investigator_id = investigator_id
        self.investigator_ip = investigator_ip
        self._sequence = 0
        self._entries: list[ForensicLogEntry] = []
        self._start_time: Optional[datetime] = None
        self._logger = logging.getLogger(f"forensic.{evidence_id[:8]}")

    def _next_seq(self) -> int:
        self._sequence += 1
        return self._sequence

    def log(
        self,
        event: ForensicEvent,
        message: Optional[str] = None,
        data: Optional[dict] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
    ) -> ForensicLogEntry:
        entry = ForensicLogEntry(
            evidence_id=self.evidence_id,
            event_type=event.value,
            sequence=self._next_seq(),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            investigator_id=self.investigator_id,
            investigator_ip=self.investigator_ip,
            message=message,
            data=data,
            duration_ms=duration_ms,
            success=success,
        )
        self._entries.append(entry)

        log_msg = f"[{entry.sequence:04d}] {event.value}"
        if message:
            log_msg += f": {message}"
        if success:
            self._logger.info(log_msg)
        else:
            self._logger.warning(log_msg)

        return entry

    def log_capture_start(self, url: str, investigator_ip: str):
        if not self._start_time:
            self._start_time = datetime.now(timezone.utc)
        self.investigator_ip = investigator_ip
        self.log(
            ForensicEvent.CAPTURE_START,
            f"Capture initiated for: {url}",
            data={
                "url": url,
                "investigator_id": self.investigator_id,
                "investigator_ip": investigator_ip,
                "platform": "INDAGO Evidence Capture v1.0",
                "standards": ["ISO/IEC 27037", "RFC 3227"],
            },
        )

    def log_dns(self, domain: str, ips: list, duration_ms: int):
        self.log(
            ForensicEvent.DNS_RESULT,
            f"DNS resolved {domain} -> {', '.join(ips)}",
            data={"domain": domain, "resolved_ips": ips},
            duration_ms=duration_ms,
        )

    def log_tls(self, domain: str, cert_info: dict):
        self.log(
            ForensicEvent.TLS_CERTIFICATE,
            f"TLS certificate verified for {domain}",
            data={"domain": domain, "certificate": cert_info},
        )

    def log_http_response(self, url: str, status: int, headers: dict, size_bytes: int):
        self.log(
            ForensicEvent.HTTP_RESPONSE,
            f"HTTP {status} from {url} ({size_bytes} bytes)",
            data={
                "url": url,
                "status_code": status,
                "headers": dict(headers),
                "size_bytes": size_bytes,
            },
        )

    def log_screenshot(self, screenshot_type: str, filename: str, sha256: str, size: tuple):
        self.log(
            ForensicEvent.SCREENSHOT_TAKEN,
            f"Screenshot captured: {screenshot_type} ({size[0]}x{size[1]})",
            data={
                "type": screenshot_type,
                "filename": filename,
                "sha256": sha256,
                "width": size[0],
                "height": size[1],
            },
        )

    def log_hash(self, filename: str, sha256: str, sha512: str, file_size: int):
        self.log(
            ForensicEvent.HASH_CALCULATED,
            f"Hash computed for {filename}",
            data={
                "filename": filename,
                "sha256": sha256,
                "sha512": sha512,
                "file_size_bytes": file_size,
                "algorithm": "SHA-256/SHA-512",
            },
        )

    def log_timestamp(self, tsa_url: str, token_received: bool):
        event = ForensicEvent.TIMESTAMP_RECEIVED if token_received else ForensicEvent.TIMESTAMP_REQUESTED
        self.log(
            event,
            f"RFC 3161 timestamp {'received' if token_received else 'requested'} from {tsa_url}",
            data={"tsa_url": tsa_url, "standard": "RFC 3161"},
            success=token_received,
        )

    def get_entries(self) -> list[ForensicLogEntry]:
        return self._entries.copy()

    def to_json_log(self) -> str:
        """Export complete forensic log as structured JSON."""
        log_data = {
            "evidence_id": self.evidence_id,
            "log_version": "1.0",
            "platform": "INDAGO Evidence Capture",
            "standard": "RFC 3227",
            "total_events": len(self._entries),
            "start_time": self._entries[0].timestamp_utc if self._entries else None,
            "end_time": self._entries[-1].timestamp_utc if self._entries else None,
            "events": [e.to_dict() for e in self._entries],
        }
        return json.dumps(log_data, ensure_ascii=False, indent=2, default=str)

    def to_list(self) -> list[dict]:
        """Return log entries as list of dicts for DB persistence."""
        return [e.to_dict() for e in self._entries]

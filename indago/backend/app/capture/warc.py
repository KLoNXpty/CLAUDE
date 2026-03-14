"""
INDAGO Evidence Capture Platform
WARC (Web Archive Format) Generator
Compliant with WARC/1.0 and WARC/1.1 specifications
"""
import io
import gzip
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

WARC_VERSION = "WARC/1.1"


def _format_warc_date(dt: Optional[datetime] = None) -> str:
    """Format datetime as WARC-Date: YYYY-MM-DDTHH:MM:SSZ"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _warc_record_id() -> str:
    """Generate a unique WARC-Record-ID."""
    return f"<urn:uuid:{uuid.uuid4()}>"


def write_warcinfo_record(output: io.BytesIO, filename: str, operator: str, url: str) -> None:
    """Write WARC warcinfo record (metadata about the archive)."""
    content = (
        f"software: INDAGO Evidence Capture Platform 1.0\r\n"
        f"operator: {operator}\r\n"
        f"target-url: {url}\r\n"
        f"format: WARC/1.1\r\n"
        f"conformsTo: https://iipc.github.io/warc-specifications/\r\n"
        f"isPartOf: INDAGO Forensic Evidence Package\r\n"
    ).encode("utf-8")

    header = (
        f"{WARC_VERSION}\r\n"
        f"WARC-Type: warcinfo\r\n"
        f"WARC-Date: {_format_warc_date()}\r\n"
        f"WARC-Filename: {filename}\r\n"
        f"WARC-Record-ID: {_warc_record_id()}\r\n"
        f"Content-Type: application/warc-fields\r\n"
        f"Content-Length: {len(content)}\r\n"
        f"\r\n"
    ).encode("utf-8")

    output.write(header)
    output.write(content)
    output.write(b"\r\n\r\n")


def write_response_record(
    output: io.BytesIO,
    url: str,
    status_code: int,
    headers: dict,
    body: bytes,
    capture_time: Optional[datetime] = None,
) -> None:
    """Write a WARC response record."""
    # Build HTTP response
    http_response = f"HTTP/1.1 {status_code}\r\n"
    for key, value in headers.items():
        http_response += f"{key}: {value}\r\n"
    http_response += "\r\n"
    http_bytes = http_response.encode("utf-8") + body

    # Compute content SHA-1 block digest (WARC standard)
    sha1 = hashlib.sha1(http_bytes).hexdigest()
    payload_sha1 = hashlib.sha1(body).hexdigest()

    header = (
        f"{WARC_VERSION}\r\n"
        f"WARC-Type: response\r\n"
        f"WARC-Date: {_format_warc_date(capture_time)}\r\n"
        f"WARC-Target-URI: {url}\r\n"
        f"WARC-Record-ID: {_warc_record_id()}\r\n"
        f"WARC-Block-Digest: sha1:{sha1}\r\n"
        f"WARC-Payload-Digest: sha1:{payload_sha1}\r\n"
        f"Content-Type: application/http; msgtype=response\r\n"
        f"Content-Length: {len(http_bytes)}\r\n"
        f"\r\n"
    ).encode("utf-8")

    output.write(header)
    output.write(http_bytes)
    output.write(b"\r\n\r\n")


def write_resource_record(
    output: io.BytesIO,
    url: str,
    content_type: str,
    content: bytes,
    capture_time: Optional[datetime] = None,
) -> None:
    """Write a WARC resource record for downloaded assets."""
    sha1 = hashlib.sha1(content).hexdigest()

    header = (
        f"{WARC_VERSION}\r\n"
        f"WARC-Type: resource\r\n"
        f"WARC-Date: {_format_warc_date(capture_time)}\r\n"
        f"WARC-Target-URI: {url}\r\n"
        f"WARC-Record-ID: {_warc_record_id()}\r\n"
        f"WARC-Block-Digest: sha1:{sha1}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(content)}\r\n"
        f"\r\n"
    ).encode("utf-8")

    output.write(header)
    output.write(content)
    output.write(b"\r\n\r\n")


def write_metadata_record(
    output: io.BytesIO,
    url: str,
    metadata_json: bytes,
    capture_time: Optional[datetime] = None,
) -> None:
    """Write a WARC metadata record."""
    sha1 = hashlib.sha1(metadata_json).hexdigest()

    header = (
        f"{WARC_VERSION}\r\n"
        f"WARC-Type: metadata\r\n"
        f"WARC-Date: {_format_warc_date(capture_time)}\r\n"
        f"WARC-Target-URI: {url}\r\n"
        f"WARC-Record-ID: {_warc_record_id()}\r\n"
        f"WARC-Block-Digest: sha1:{sha1}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(metadata_json)}\r\n"
        f"\r\n"
    ).encode("utf-8")

    output.write(header)
    output.write(metadata_json)
    output.write(b"\r\n\r\n")


class WARCBuilder:
    """
    Build a complete WARC archive for a forensic evidence package.
    """

    def __init__(self, output_path: Path, url: str, operator: str = "INDAGO"):
        self.output_path = output_path
        self.url = url
        self.operator = operator
        self._buffer = io.BytesIO()
        self._record_count = 0

    def start(self):
        """Write WARC header."""
        write_warcinfo_record(
            self._buffer,
            filename=self.output_path.name,
            operator=self.operator,
            url=self.url,
        )

    def add_response(self, url: str, status: int, headers: dict, body: bytes, capture_time=None):
        """Add HTTP response record."""
        write_response_record(self._buffer, url, status, headers, body, capture_time)
        self._record_count += 1

    def add_resource(self, url: str, content_type: str, content: bytes, capture_time=None):
        """Add resource record."""
        write_resource_record(self._buffer, url, content_type, content, capture_time)
        self._record_count += 1

    def add_metadata(self, url: str, metadata: dict, capture_time=None):
        """Add metadata JSON record."""
        import json
        metadata_bytes = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
        write_metadata_record(self._buffer, url, metadata_bytes, capture_time)
        self._record_count += 1

    def save(self) -> Path:
        """Save WARC file (gzip compressed)."""
        warc_gz_path = self.output_path.with_suffix(".warc.gz")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with gzip.open(str(warc_gz_path), "wb", compresslevel=9) as gz_file:
            gz_file.write(self._buffer.getvalue())

        logger.info(f"WARC archive saved: {warc_gz_path} ({self._record_count} records)")
        return warc_gz_path

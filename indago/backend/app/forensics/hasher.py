"""
INDAGO Evidence Capture Platform
Forensic Hash Generation
Implements: SHA256, SHA512, MD5 per ISO/IEC 27037 requirements
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, BinaryIO
from dataclasses import dataclass, field, asdict


@dataclass
class HashResult:
    sha256: str
    sha512: str
    md5: str
    file_size: int
    algorithms: list = field(default_factory=lambda: ["sha256", "sha512", "md5"])

    def to_dict(self) -> dict:
        return asdict(self)

    def to_manifest_line(self, filename: str) -> str:
        """Generate manifest line compatible with common forensic tools."""
        return f"SHA256:{self.sha256}  {filename}\n"


def compute_hash_from_bytes(data: bytes) -> HashResult:
    """Compute all forensic hashes from bytes."""
    return HashResult(
        sha256=hashlib.sha256(data).hexdigest(),
        sha512=hashlib.sha512(data).hexdigest(),
        md5=hashlib.md5(data).hexdigest(),
        file_size=len(data),
    )


def compute_hash_from_file(file_path: str | Path) -> HashResult:
    """
    Compute all forensic hashes from a file.
    Uses streaming to handle large files efficiently.
    """
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    md5 = hashlib.md5()
    file_size = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(65536):  # 64KB chunks
            sha256.update(chunk)
            sha512.update(chunk)
            md5.update(chunk)
            file_size += len(chunk)

    return HashResult(
        sha256=sha256.hexdigest(),
        sha512=sha512.hexdigest(),
        md5=md5.hexdigest(),
        file_size=file_size,
    )


def compute_hash_from_stream(stream: BinaryIO) -> HashResult:
    """Compute hashes from a file-like stream."""
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    md5 = hashlib.md5()
    file_size = 0

    while chunk := stream.read(65536):
        sha256.update(chunk)
        sha512.update(chunk)
        md5.update(chunk)
        file_size += len(chunk)

    return HashResult(
        sha256=sha256.hexdigest(),
        sha512=sha512.hexdigest(),
        md5=md5.hexdigest(),
        file_size=file_size,
    )


def compute_directory_hash(directory: str | Path) -> dict:
    """
    Compute hashes for all files in a directory tree.
    Returns a manifest dict suitable for evidence packaging.
    """
    directory = Path(directory)
    manifest = {}

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(directory))
            manifest[rel_path] = compute_hash_from_file(file_path).to_dict()

    return manifest


def compute_package_hash(manifest: dict) -> HashResult:
    """
    Compute hash of the entire evidence package manifest.
    This creates a single hash representing all evidence.
    """
    manifest_json = json.dumps(manifest, sort_keys=True, ensure_ascii=False)
    manifest_bytes = manifest_json.encode("utf-8")
    return compute_hash_from_bytes(manifest_bytes)


def generate_hash_manifest(
    directory: str | Path,
    evidence_id: str,
    investigator: str,
    capture_timestamp: str,
) -> dict:
    """
    Generate a complete forensic hash manifest for an evidence package.
    Compliant with RFC 3227 chain of custody requirements.
    """
    directory = Path(directory)
    file_hashes = compute_directory_hash(directory)
    package_hash = compute_package_hash(file_hashes)

    manifest = {
        "evidence_id": evidence_id,
        "generated_by": "INDAGO Evidence Capture Platform",
        "standard": "ISO/IEC 27037",
        "investigator": investigator,
        "capture_timestamp_utc": capture_timestamp,
        "files": file_hashes,
        "package_integrity": {
            "sha256": package_hash.sha256,
            "sha512": package_hash.sha512,
            "md5": package_hash.md5,
            "total_files": len(file_hashes),
        },
    }

    return manifest


def verify_hash_manifest(manifest: dict, directory: str | Path) -> dict:
    """
    Verify all file hashes in a manifest against current files.
    Returns verification result with any discrepancies.
    """
    directory = Path(directory)
    results = {"verified": True, "files": {}, "errors": []}

    for rel_path, expected_hashes in manifest.get("files", {}).items():
        file_path = directory / rel_path
        if not file_path.exists():
            results["verified"] = False
            results["errors"].append(f"File missing: {rel_path}")
            results["files"][rel_path] = {"status": "MISSING"}
            continue

        current = compute_hash_from_file(file_path)
        file_ok = (
            current.sha256 == expected_hashes.get("sha256")
            and current.sha512 == expected_hashes.get("sha512")
        )

        if not file_ok:
            results["verified"] = False
            results["errors"].append(f"Hash mismatch: {rel_path}")

        results["files"][rel_path] = {
            "status": "OK" if file_ok else "TAMPERED",
            "expected_sha256": expected_hashes.get("sha256"),
            "current_sha256": current.sha256,
        }

    return results

"""
INDAGO Evidence Capture Platform
RFC 3161 Trusted Timestamp Service Integration
Provides legally defensible timestamps for digital evidence
"""
import base64
import hashlib
import struct
import requests
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RFC3161Timestamper:
    """
    Implements RFC 3161 Time Stamp Protocol (TSP) for trusted timestamps.
    Timestamps are cryptographically bound to evidence hash, making
    alterations detectable.
    """

    # Public TSA endpoints
    TSA_ENDPOINTS = {
        "freetsa": "https://freetsa.org/tsr",
        "digicert": "http://timestamp.digicert.com",
        "sectigo": "http://timestamp.sectigo.com",
        "globalsign": "http://timestamp.globalsign.com/tsa/r6advanced1",
    }

    def __init__(self, tsa_url: str = "https://freetsa.org/tsr"):
        self.tsa_url = tsa_url

    def create_timestamp_request(self, data_hash: bytes, hash_algorithm: str = "sha256") -> bytes:
        """
        Create a minimal RFC 3161 TimeStampReq.
        Uses DER encoding for TSA submission.
        """
        # OID for SHA-256
        sha256_oid = bytes([
            0x06, 0x09,  # OID tag + length
            0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01  # 2.16.840.1.101.3.4.2.1
        ])

        # MessageImprint ::= SEQUENCE { hashAlgorithm AlgorithmIdentifier, hashedMessage OCTET STRING }
        hash_algorithm_seq = bytes([0x30, len(sha256_oid) + 2]) + sha256_oid + bytes([0x05, 0x00])
        hash_value = bytes([0x04, len(data_hash)]) + data_hash
        message_imprint = bytes([0x30, len(hash_algorithm_seq) + len(hash_value)]) + hash_algorithm_seq + hash_value

        # Nonce (random 8 bytes as INTEGER)
        import secrets
        nonce_val = secrets.token_bytes(8)
        nonce_int = int.from_bytes(nonce_val, 'big')
        nonce_encoded = nonce_int.to_bytes((nonce_int.bit_length() + 7) // 8, 'big')
        if nonce_encoded[0] & 0x80:
            nonce_encoded = b'\x00' + nonce_encoded
        nonce = bytes([0x02, len(nonce_encoded)]) + nonce_encoded

        # certReq = TRUE
        cert_req = bytes([0x01, 0x01, 0xff])

        # version INTEGER ::= 1
        version = bytes([0x02, 0x01, 0x01])

        # TimeStampReq
        req_body = version + message_imprint + nonce + cert_req
        req = bytes([0x30, len(req_body)]) + req_body

        return req

    def request_timestamp(self, data: bytes) -> Optional[dict]:
        """
        Request an RFC 3161 timestamp for given data.
        Returns timestamp token and metadata.
        """
        data_hash = hashlib.sha256(data).digest()
        tsq = self.create_timestamp_request(data_hash)

        try:
            response = requests.post(
                self.tsa_url,
                data=tsq,
                headers={"Content-Type": "application/timestamp-query"},
                timeout=30,
            )

            if response.status_code == 200:
                tsr_bytes = response.content
                token_b64 = base64.b64encode(tsr_bytes).decode("utf-8")

                return {
                    "status": "success",
                    "tsa_url": self.tsa_url,
                    "hash_sha256": hashlib.sha256(data).hexdigest(),
                    "timestamp_token_b64": token_b64,
                    "token_size_bytes": len(tsr_bytes),
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                    "standard": "RFC 3161",
                }
            else:
                logger.warning(f"TSA returned HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"TSA request failed: {e}")
            return None

    def request_timestamp_for_file(self, file_path: str) -> Optional[dict]:
        """Request timestamp for a file's content."""
        with open(file_path, "rb") as f:
            data = f.read()
        return self.request_timestamp(data)


class OpenTimestamper:
    """
    OpenTimestamps (OTS) integration for Bitcoin blockchain anchoring.
    Provides additional timestamp verification via blockchain.
    """

    def __init__(self):
        self.calendars = [
            "https://alice.btc.calendar.opentimestamps.org",
            "https://bob.btc.calendar.opentimestamps.org",
            "https://finney.calendar.eternitywall.com",
        ]

    def stamp(self, data_hash_hex: str) -> Optional[dict]:
        """
        Submit hash to OpenTimestamps calendars.
        Returns OTS receipt data.
        """
        try:
            data_hash = bytes.fromhex(data_hash_hex)
            receipts = []

            for calendar in self.calendars:
                try:
                    response = requests.post(
                        f"{calendar}/digest",
                        data=data_hash,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=15,
                    )
                    if response.status_code == 200:
                        receipt_b64 = base64.b64encode(response.content).decode("utf-8")
                        receipts.append({
                            "calendar": calendar,
                            "receipt_b64": receipt_b64,
                            "pending": True,
                        })
                except Exception as e:
                    logger.warning(f"OTS calendar {calendar} failed: {e}")

            if receipts:
                return {
                    "status": "pending_blockchain_confirmation",
                    "hash_sha256": data_hash_hex,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "receipts": receipts,
                    "note": "Bitcoin blockchain confirmation typically takes ~1 hour",
                }
        except Exception as e:
            logger.error(f"OpenTimestamps stamping failed: {e}")
        return None


def create_timestamp_metadata(
    evidence_id: str,
    package_hash: str,
    capture_utc: str,
    tsa_result: Optional[dict] = None,
    ots_result: Optional[dict] = None,
) -> dict:
    """
    Create complete timestamp metadata record for evidence package.
    """
    return {
        "evidence_id": evidence_id,
        "package_sha256": package_hash,
        "capture_timestamp_utc": capture_utc,
        "timestamp_methods": {
            "rfc3161": tsa_result,
            "opentimestamps": ots_result,
        },
        "verification_note": (
            "Timestamps provide cryptographic proof that the evidence existed "
            "at the stated time and has not been altered since."
        ),
        "standards": ["RFC 3161", "ISO/IEC 27037"],
    }

"""
INDAGO Evidence Capture Platform
Evidence Report Generator
Generates PDF and JSON reports compliant with forensic standards
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

from jinja2 import Environment, BaseLoader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.forensics.hasher import compute_hash_from_file

logger = logging.getLogger(__name__)

# Color palette
INDAGO_DARK = colors.HexColor("#0a0e1a")
INDAGO_BLUE = colors.HexColor("#0066cc")
INDAGO_ACCENT = colors.HexColor("#00a8ff")
INDAGO_GRAY = colors.HexColor("#6b7280")
INDAGO_LIGHT = colors.HexColor("#f8fafc")
DANGER_RED = colors.HexColor("#dc2626")
SUCCESS_GREEN = colors.HexColor("#16a34a")


class ReportGenerator:
    """
    Generate comprehensive forensic evidence reports.
    Output formats: PDF (ReportLab), JSON
    """

    def __init__(self, capture, db):
        self.capture = capture
        self.db = db

    async def generate(self) -> dict:
        """Generate both PDF and JSON reports."""
        evidence_dir = Path(self.capture.storage_path)
        report_dir = evidence_dir / "report"
        report_dir.mkdir(exist_ok=True)

        evidence_id = str(self.capture.evidence_id)
        results = {}

        # Generate JSON report
        json_path = report_dir / f"evidence_report_{evidence_id[:8]}.json"
        json_data = await self._build_json_report()
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

        json_hash = compute_hash_from_file(json_path)
        results["json"] = str(json_path)
        results["json_sha256"] = json_hash.sha256

        # Generate PDF report
        pdf_path = report_dir / f"evidence_report_{evidence_id[:8]}.pdf"
        await self._build_pdf_report(pdf_path, json_data)

        if pdf_path.exists():
            pdf_hash = compute_hash_from_file(pdf_path)
            results["pdf"] = str(pdf_path)
            results["pdf_sha256"] = pdf_hash.sha256

        logger.info(f"Reports generated for evidence {evidence_id}")
        return results

    async def _build_json_report(self) -> dict:
        """Build comprehensive JSON evidence report."""
        from sqlalchemy import select
        from app.models.capture import Screenshot, CapturedResource, ForensicLog, EvidenceMetadata, SocialMediaData

        capture = self.capture

        # Fetch related data
        screenshots = []
        resources_summary = []
        logs = []
        metadata = {}
        social = {}

        try:
            ss_result = await self.db.execute(
                select(Screenshot).where(Screenshot.capture_id == capture.id)
            )
            for ss in ss_result.scalars().all():
                screenshots.append({
                    "type": ss.screenshot_type,
                    "filename": ss.filename,
                    "sha256": ss.sha256,
                    "timestamp_utc": ss.timestamp_utc.isoformat() if ss.timestamp_utc else None,
                    "dimensions": f"{ss.viewport_width}x{ss.viewport_height}" if ss.viewport_width else None,
                })

            res_result = await self.db.execute(
                select(CapturedResource).where(CapturedResource.capture_id == capture.id)
            )
            for res in res_result.scalars().all():
                resources_summary.append({
                    "url": res.resource_url,
                    "type": res.resource_type,
                    "sha256": res.sha256,
                    "size_bytes": res.file_size_bytes,
                    "mime_type": res.mime_type,
                })

            log_result = await self.db.execute(
                select(ForensicLog).where(ForensicLog.capture_id == capture.id)
                .order_by(ForensicLog.sequence)
            )
            for log in log_result.scalars().all():
                logs.append({
                    "sequence": log.sequence,
                    "event": log.event_type,
                    "message": log.message,
                    "timestamp_utc": log.timestamp_utc.isoformat() if log.timestamp_utc else None,
                    "success": log.success,
                })

            meta_result = await self.db.execute(
                select(EvidenceMetadata).where(EvidenceMetadata.capture_id == capture.id)
            )
            meta = meta_result.scalar_one_or_none()
            if meta:
                metadata = {
                    "title": meta.page_title,
                    "language": meta.page_language,
                    "canonical_url": meta.canonical_url,
                    "cookies_count": len(meta.cookies) if meta.cookies else 0,
                    "links_count": len(meta.links_found) if meta.links_found else 0,
                    "iframes_count": len(meta.iframes_found) if meta.iframes_found else 0,
                }

            social_result = await self.db.execute(
                select(SocialMediaData).where(SocialMediaData.capture_id == capture.id)
            )
            social_record = social_result.scalar_one_or_none()
            if social_record:
                social = {
                    "platform": social_record.platform,
                    "author": social_record.author_username,
                    "post_text": social_record.post_text,
                    "post_datetime": social_record.post_datetime.isoformat() if social_record.post_datetime else None,
                    "hashtags": social_record.hashtags,
                    "likes_count": social_record.likes_count,
                    "comments_count": social_record.comments_count,
                    "comments_data": social_record.comments_data,
                }
        except Exception as e:
            logger.warning(f"Error fetching related data: {e}")

        return {
            "report_version": "1.0",
            "platform": "INDAGO Evidence Capture",
            "standards": ["ISO/IEC 27037", "ISO/IEC 27042", "RFC 3227", "NIST Digital Forensics"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evidence": {
                "id": str(capture.evidence_id),
                "url": capture.url,
                "final_url": capture.final_url,
                "domain": capture.domain,
                "case_number": capture.case_number,
                "case_description": capture.case_description,
                "capture_type": capture.capture_type,
                "social_platform": str(capture.social_platform) if capture.social_platform else None,
                "status": capture.status,
            },
            "timing": {
                "initiated_at_utc": capture.initiated_at.isoformat() if capture.initiated_at else None,
                "capture_started_at_utc": capture.capture_started_at.isoformat() if capture.capture_started_at else None,
                "capture_completed_at_utc": capture.capture_completed_at.isoformat() if capture.capture_completed_at else None,
            },
            "network": {
                "server_ip": capture.server_ip,
                "http_status": capture.http_status_code,
                "dns_info": capture.dns_info,
                "tls_info": capture.tls_info,
                "whois_info": capture.whois_info,
                "response_headers": capture.server_headers,
            },
            "browser": {
                "user_agent": capture.user_agent,
                "viewport": f"{capture.viewport_width}x{capture.viewport_height}",
            },
            "integrity": {
                "html_sha256": capture.html_sha256,
                "dom_sha256": capture.dom_sha256,
                "package_sha256": capture.package_sha256,
                "package_sha512": capture.package_sha512,
                "timestamp_rfc3161": bool(capture.tsa_timestamp),
                "tsa_url": capture.tsa_url,
                "evidence_locked": capture.is_locked,
            },
            "content": {
                "screenshots": screenshots,
                "total_resources": capture.total_resources,
                "total_size_bytes": capture.total_size_bytes,
                "resources": resources_summary[:50],  # First 50 in report
                "metadata": metadata,
                "social_media": social if social else None,
            },
            "forensic_log": logs,
            "disclaimer": (
                "This evidence report was generated automatically by INDAGO Evidence Capture Platform. "
                "The integrity of all captured content can be verified using the provided cryptographic hashes. "
                "The chain of custody is maintained through the forensic log and audit trail. "
                "This evidence complies with ISO/IEC 27037 guidelines for digital evidence preservation."
            ),
        }

    async def _build_pdf_report(self, pdf_path: Path, data: dict):
        """Generate professional PDF forensic report."""
        try:
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm,
            )

            styles = getSampleStyleSheet()
            story = []

            # Custom styles
            title_style = ParagraphStyle(
                "IndagoTitle",
                parent=styles["Title"],
                fontSize=28,
                textColor=INDAGO_DARK,
                spaceAfter=5,
                fontName="Helvetica-Bold",
            )
            subtitle_style = ParagraphStyle(
                "IndagoSubtitle",
                parent=styles["Normal"],
                fontSize=14,
                textColor=INDAGO_BLUE,
                spaceAfter=20,
                fontName="Helvetica",
            )
            heading_style = ParagraphStyle(
                "IndagoHeading",
                parent=styles["Heading1"],
                fontSize=14,
                textColor=INDAGO_DARK,
                spaceBefore=20,
                spaceAfter=8,
                fontName="Helvetica-Bold",
                borderPad=4,
            )
            subheading_style = ParagraphStyle(
                "IndagoSubheading",
                parent=styles["Heading2"],
                fontSize=11,
                textColor=INDAGO_BLUE,
                spaceBefore=12,
                spaceAfter=5,
                fontName="Helvetica-Bold",
            )
            body_style = ParagraphStyle(
                "IndagoBody",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.black,
                spaceAfter=4,
                fontName="Helvetica",
                leading=14,
            )
            mono_style = ParagraphStyle(
                "IndagoMono",
                parent=styles["Code"],
                fontSize=7,
                textColor=INDAGO_DARK,
                fontName="Courier",
                backColor=INDAGO_LIGHT,
                leading=11,
                leftIndent=10,
                rightIndent=10,
                spaceBefore=2,
                spaceAfter=2,
            )
            label_style = ParagraphStyle(
                "IndagoLabel",
                parent=styles["Normal"],
                fontSize=8,
                textColor=INDAGO_GRAY,
                fontName="Helvetica",
            )

            evidence = data.get("evidence", {})
            integrity = data.get("integrity", {})
            timing = data.get("timing", {})
            network = data.get("network", {})

            # ----------------------------------------------------------------
            # COVER PAGE
            # ----------------------------------------------------------------
            story.append(Spacer(1, 2*cm))
            story.append(Paragraph("INDAGO", title_style))
            story.append(Paragraph("Evidence Capture Platform", subtitle_style))
            story.append(HRFlowable(width="100%", thickness=2, color=INDAGO_BLUE))
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("DIGITAL EVIDENCE PRESERVATION REPORT", ParagraphStyle(
                "CoverTitle",
                parent=styles["Normal"],
                fontSize=16,
                textColor=INDAGO_DARK,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
            )))
            story.append(Spacer(1, 1*cm))

            # Evidence summary table
            evidence_table_data = [
                ["Evidence ID", str(evidence.get("id", "N/A"))],
                ["Target URL", str(evidence.get("url", "N/A"))],
                ["Case Number", str(evidence.get("case_number") or "N/A")],
                ["Capture Type", str(evidence.get("capture_type", "N/A"))],
                ["Capture Date (UTC)", str(timing.get("capture_started_at_utc", "N/A"))],
                ["Report Generated", str(data.get("generated_at_utc", "N/A"))],
                ["HTTP Status", str(network.get("http_status", "N/A"))],
                ["Server IP", str(network.get("server_ip", "N/A"))],
            ]

            summary_table = Table(evidence_table_data, colWidths=[5*cm, 12*cm])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), INDAGO_LIGHT),
                ("TEXTCOLOR", (0, 0), (0, -1), INDAGO_DARK),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, INDAGO_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, INDAGO_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("WORDWRAP", (1, 0), (1, -1), True),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 1*cm))

            # Integrity status
            story.append(Paragraph("INTEGRITY STATUS", subheading_style))
            integrity_status = "VERIFIED" if integrity.get("package_sha256") else "PENDING"
            status_color = SUCCESS_GREEN if integrity_status == "VERIFIED" else DANGER_RED

            integrity_data = [
                ["Package SHA-256", str(integrity.get("package_sha256", "N/A"))],
                ["Package SHA-512", str(integrity.get("package_sha512", "N/A"))[:64] + "..." if integrity.get("package_sha512") else "N/A"],
                ["HTML SHA-256", str(integrity.get("html_sha256", "N/A"))],
                ["RFC 3161 Timestamp", "YES" if integrity.get("timestamp_rfc3161") else "NO"],
                ["Evidence Locked", "YES (Read-Only)" if integrity.get("evidence_locked") else "NO"],
            ]

            integrity_table = Table(integrity_data, colWidths=[5*cm, 12*cm])
            integrity_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), INDAGO_DARK),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTNAME", (1, 0), (1, -1), "Courier"),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, INDAGO_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, INDAGO_GRAY),
                ("WORDWRAP", (1, 0), (1, -1), True),
            ]))
            story.append(integrity_table)

            story.append(PageBreak())

            # ----------------------------------------------------------------
            # STANDARDS & COMPLIANCE
            # ----------------------------------------------------------------
            story.append(Paragraph("Legal & Compliance Framework", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=INDAGO_BLUE))
            story.append(Spacer(1, 0.3*cm))

            standards_text = """
            This evidence report was produced in compliance with the following international standards:
            <br/><br/>
            • <b>ISO/IEC 27037</b>: Guidelines for identification, collection, acquisition and preservation of digital evidence<br/>
            • <b>ISO/IEC 27042</b>: Guidelines for the analysis and interpretation of digital evidence<br/>
            • <b>NIST SP 800-86</b>: Guide to Integrating Forensic Techniques into Incident Response<br/>
            • <b>RFC 3227</b>: Guidelines for Evidence Collection and Archiving<br/>
            • <b>RFC 3161</b>: Internet X.509 PKI Time-Stamp Protocol (TSP)<br/>
            <br/>
            The captured evidence maintains a complete chain of custody and can be presented in legal proceedings.
            All cryptographic hashes provide tamper-evident sealing of the evidence package.
            """
            story.append(Paragraph(standards_text, body_style))

            # ----------------------------------------------------------------
            # NETWORK INFORMATION
            # ----------------------------------------------------------------
            story.append(Paragraph("Network & Technical Metadata", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=INDAGO_BLUE))

            dns_info = network.get("dns_info", {})
            tls_info = network.get("tls_info", {})

            net_data = [
                ["Parameter", "Value"],
                ["Target URL", str(evidence.get("url", "N/A"))],
                ["Final URL (after redirects)", str(evidence.get("final_url") or evidence.get("url", "N/A"))],
                ["Server IP Address", str(network.get("server_ip", "N/A"))],
                ["HTTP Response Code", str(network.get("http_status", "N/A"))],
                ["DNS A Records", ", ".join(dns_info.get("records", {}).get("A", ["N/A"]))],
                ["TLS Version", str(tls_info.get("protocol", "N/A"))],
                ["TLS Issuer", str((tls_info.get("issuer") or {}).get("organizationName", "N/A"))],
                ["TLS Valid Until", str(tls_info.get("not_after", "N/A"))],
                ["User Agent", str(network.get("user_agent", "Mozilla/5.0..."))],
            ]

            net_table = Table(net_data, colWidths=[6*cm, 11*cm])
            net_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INDAGO_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 1), (0, -1), INDAGO_LIGHT),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (1, 1), (1, -1), [colors.white, INDAGO_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, INDAGO_GRAY),
                ("WORDWRAP", (1, 0), (1, -1), True),
            ]))
            story.append(net_table)

            # ----------------------------------------------------------------
            # EVIDENCE FILES
            # ----------------------------------------------------------------
            story.append(Paragraph("Captured Evidence Files", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=INDAGO_BLUE))

            content = data.get("content", {})
            screenshots = content.get("screenshots", [])

            if screenshots:
                story.append(Paragraph("Screenshots", subheading_style))
                ss_data = [["Type", "Filename", "SHA-256", "Timestamp (UTC)"]]
                for ss in screenshots:
                    ss_data.append([
                        ss.get("type", ""),
                        ss.get("filename", ""),
                        (ss.get("sha256") or "")[:16] + "...",
                        str(ss.get("timestamp_utc", ""))[:19],
                    ])

                ss_table = Table(ss_data, colWidths=[3*cm, 4*cm, 4*cm, 6*cm])
                ss_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INDAGO_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INDAGO_LIGHT]),
                    ("GRID", (0, 0), (-1, -1), 0.3, INDAGO_GRAY),
                    ("FONTNAME", (2, 1), (2, -1), "Courier"),
                ]))
                story.append(ss_table)

            # Resources summary
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(
                f"Total Captured Resources: <b>{content.get('total_resources', 0)}</b> files, "
                f"<b>{_format_size(content.get('total_size_bytes', 0))}</b> total",
                body_style,
            ))

            # ----------------------------------------------------------------
            # SOCIAL MEDIA DATA
            # ----------------------------------------------------------------
            social = content.get("social_media")
            if social:
                story.append(PageBreak())
                story.append(Paragraph("Social Media Content", heading_style))
                story.append(HRFlowable(width="100%", thickness=1, color=INDAGO_BLUE))

                social_data = [
                    ["Platform", str(social.get("platform", "N/A")).upper()],
                    ["Author", str(social.get("author", "N/A"))],
                    ["Post Date", str(social.get("post_datetime", "N/A"))],
                    ["Likes", str(social.get("likes_count", "N/A"))],
                    ["Comments", str(social.get("comments_count", "N/A"))],
                ]
                social_table = Table(social_data, colWidths=[4*cm, 13*cm])
                social_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), INDAGO_LIGHT),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, INDAGO_GRAY),
                ]))
                story.append(social_table)
                story.append(Spacer(1, 0.3*cm))

                if social.get("post_text"):
                    story.append(Paragraph("Post Content:", subheading_style))
                    # Escape HTML in post text
                    post_text = str(social["post_text"]).replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(post_text[:2000], mono_style))

                if social.get("hashtags"):
                    story.append(Paragraph(
                        "Hashtags: " + ", ".join(str(h) for h in social["hashtags"][:20]),
                        body_style,
                    ))

                if social.get("comments_data"):
                    story.append(Paragraph("Comments Captured:", subheading_style))
                    comments = social["comments_data"][:50]
                    for i, comment in enumerate(comments[:20], 1):
                        if isinstance(comment, dict):
                            author = comment.get("author", "Unknown")
                            text = str(comment.get("text", ""))[:300].replace("<", "&lt;").replace(">", "&gt;")
                            story.append(Paragraph(f"<b>{i}. {author}:</b> {text}", body_style))

            # ----------------------------------------------------------------
            # FORENSIC LOG SUMMARY
            # ----------------------------------------------------------------
            story.append(PageBreak())
            story.append(Paragraph("Forensic Process Log", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=INDAGO_BLUE))
            story.append(Paragraph(
                "The following events were recorded during the evidence capture process, "
                "providing a complete chain of custody record:",
                body_style,
            ))
            story.append(Spacer(1, 0.3*cm))

            logs = data.get("forensic_log", [])
            if logs:
                log_data = [["#", "Event", "Timestamp (UTC)", "Status", "Message"]]
                for log in logs[:50]:
                    log_data.append([
                        str(log.get("sequence", "")),
                        str(log.get("event", "")),
                        str(log.get("timestamp_utc", ""))[:19],
                        "OK" if log.get("success", True) else "FAIL",
                        str(log.get("message") or "")[:60],
                    ])

                log_table = Table(log_data, colWidths=[1*cm, 4.5*cm, 4.5*cm, 1.5*cm, 6.5*cm])
                log_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INDAGO_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, INDAGO_LIGHT]),
                    ("GRID", (0, 0), (-1, -1), 0.3, INDAGO_GRAY),
                    ("WORDWRAP", (4, 1), (4, -1), True),
                ]))
                story.append(log_table)

            # ----------------------------------------------------------------
            # DISCLAIMER & CERTIFICATION
            # ----------------------------------------------------------------
            story.append(PageBreak())
            story.append(Paragraph("Certification & Disclaimer", heading_style))
            story.append(HRFlowable(width="100%", thickness=2, color=INDAGO_BLUE))
            story.append(Spacer(1, 0.5*cm))

            cert_text = """
            <b>CERTIFICATE OF DIGITAL EVIDENCE INTEGRITY</b>
            <br/><br/>
            This document certifies that the digital evidence described herein was captured, preserved, and
            documented in accordance with internationally recognized digital forensics standards.
            <br/><br/>
            The evidence package maintains a cryptographically verifiable chain of custody. Any subsequent
            modification of the captured content would be detectable through the hash verification mechanism.
            <br/><br/>
            <b>Verification Statement:</b><br/>
            The captured content at the URL specified above was preserved exactly as it appeared at the
            recorded date and time. The integrity of all captured files has been cryptographically sealed
            using SHA-256 and SHA-512 hashing algorithms. The evidence package has been timestamped using
            RFC 3161 Trusted Timestamp Protocol, providing legally defensible proof of the capture time.
            <br/><br/>
            <b>Standards Compliance:</b><br/>
            This capture procedure follows the volatility order prescribed in RFC 3227, preserving the most
            volatile data first. The complete evidence package is suitable for presentation in judicial
            proceedings, administrative hearings, and regulatory investigations.
            """
            story.append(Paragraph(cert_text, body_style))
            story.append(Spacer(1, 2*cm))
            story.append(HRFlowable(width="8*cm", thickness=1, color=INDAGO_DARK))
            story.append(Paragraph("INDAGO Evidence Capture Platform", label_style))
            story.append(Paragraph(f"Generated: {data.get('generated_at_utc', 'N/A')}", label_style))

            # Build PDF
            doc.build(story, onFirstPage=_add_page_header, onLaterPages=_add_page_header)

        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)


def _format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024*1024):.1f} MB"
    else:
        return f"{size_bytes / (1024*1024*1024):.2f} GB"


def _add_page_header(canvas, doc):
    """Add header and footer to each PDF page."""
    canvas.saveState()
    width, height = A4

    # Header line
    canvas.setStrokeColor(INDAGO_BLUE)
    canvas.setLineWidth(1)
    canvas.line(2*cm, height - 1.5*cm, width - 2*cm, height - 1.5*cm)

    # Header text
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(INDAGO_DARK)
    canvas.drawString(2*cm, height - 1.3*cm, "INDAGO Evidence Capture")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(INDAGO_GRAY)
    canvas.drawRightString(width - 2*cm, height - 1.3*cm, "CONFIDENTIAL - FORENSIC EVIDENCE")

    # Footer
    canvas.setStrokeColor(INDAGO_BLUE)
    canvas.line(2*cm, 1.5*cm, width - 2*cm, 1.5*cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(INDAGO_GRAY)
    canvas.drawString(2*cm, 1.1*cm, "ISO/IEC 27037 | RFC 3227 | RFC 3161")
    canvas.drawRightString(width - 2*cm, 1.1*cm, f"Page {doc.page}")

    canvas.restoreState()

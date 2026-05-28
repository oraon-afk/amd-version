from __future__ import annotations

import json
import textwrap
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.audit import ReportResponse
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{audit_id}", response_model=ReportResponse)
def get_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    return audit_service.get_report(db=db, user=current_user, audit_id=audit_id)


@router.get("/{audit_id}/download/json")
def download_report_json(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = audit_service.get_report(db=db, user=current_user, audit_id=audit_id)
    payload = {
        "id": report.id,
        "audit_id": report.audit_id,
        "summary": report.summary,
        "report_payload": report.report_payload,
        "report_json_s3_uri": report.report_json_s3_uri,
        "created_at": report.created_at.isoformat() if isinstance(report.created_at, datetime) else report.created_at,
    }
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="audit-report-{audit_id}.json"'},
    )


@router.get("/{audit_id}/download/pdf")
def download_report_pdf(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = audit_service.get_report(db=db, user=current_user, audit_id=audit_id)
    lines = [
        "AI Audit Report",
        f"Audit ID: {report.audit_id}",
        f"Generated: {report.created_at.isoformat() if report.created_at else ''}",
        "",
        "Summary",
        report.summary,
        "",
        "Payload",
        json.dumps(report.report_payload, indent=2, default=str),
    ]
    pdf = _simple_pdf("\n".join(lines))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit-report-{audit_id}.pdf"'},
    )


def _simple_pdf(text: str) -> bytes:
    escaped_lines: list[str] = []
    for raw_line in text.splitlines():
        for line in textwrap.wrap(raw_line, width=92) or [""]:
            escaped_lines.append(_escape_pdf_text(line))
    escaped_lines = escaped_lines[:58]

    content_lines = ["BT", "/F1 10 Tf", "12 TL", "50 792 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({line}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"),
    )
    return bytes(pdf)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

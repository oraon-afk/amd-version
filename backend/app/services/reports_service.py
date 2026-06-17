from datetime import datetime
import io
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.models.ai_features import CustomReport, RemediationPlan
from backend.app.db.models.audit import AuditReport, AuditRun, EvidenceLink, Finding
from backend.app.db.models.document import UploadedDocument
from backend.app.db.models.user import User
from backend.app.services.llm_service import llm_service

logger = get_logger(__name__)

class ReportsService:
    async def generate_custom_report(
        self,
        *,
        db: Session,
        user: User,
        audit_id: str,
        template: str,
        sections: list[str],
    ) -> CustomReport:
        """Generate an AI-rewritten custom compliance report tailored to a specific audience template."""
        logger.info("Generating custom report for audit %s, template %s", audit_id, template)

        # 1. Fetch Audit, Findings, Remediation Plans, Evidence
        statement = select(AuditRun).where(AuditRun.id == audit_id)
        if (user.role or "").upper() not in {"ADMIN", "REVIEWER"}:
            statement = statement.where(AuditRun.user_id == user.id)
        audit = db.scalar(statement)
        if not audit:
            raise ValueError("Audit not found or access denied.")

        findings = list(db.scalars(select(Finding).where(Finding.audit_id == audit_id)))
        finding_ids = [f.id for f in findings]
        
        remediations = []
        if finding_ids:
            remediations = list(db.scalars(select(RemediationPlan).where(RemediationPlan.finding_id.in_(finding_ids))))
        
        evidence = []
        if finding_ids:
            evidence = list(db.scalars(select(EvidenceLink).where(EvidenceLink.finding_id.in_(finding_ids))))

        doc = db.get(UploadedDocument, audit.document_id)
        doc_title = doc.title if doc else "Unknown Document"

        # Calculate metrics
        total_findings = len(findings)
        high_severity = sum(1 for f in findings if (f.severity or "").upper() in ("HIGH", "CRITICAL"))
        medium_severity = sum(1 for f in findings if (f.severity or "").upper() == "MEDIUM")
        low_severity = sum(1 for f in findings if (f.severity or "").upper() == "LOW")

        # 2. Setup standard metadata
        report_title = f"{template} Compliance Assessment Report"
        generated_data = {
            "title": report_title,
            "metadata": {
                "audit_id": audit_id,
                "document_title": doc_title,
                "template": template,
                "generated_at": datetime.utcnow().isoformat(),
                "overall_risk": audit.overall_risk or "UNKNOWN",
                "compliance_score": getattr(audit, "compliance_score", 0),
                "total_findings": total_findings,
                "high_severity": high_severity,
                "medium_severity": medium_severity,
                "low_severity": low_severity,
            },
            "sections": {}
        }

        # 3. Generate narrative text for each requested section
        for section_name in sections:
            section_key = section_name.strip().lower()
            narrative = await self._generate_section_narrative(
                template=template,
                section_name=section_name,
                audit_meta=generated_data["metadata"],
                findings=findings,
                remediations=remediations,
                evidence=evidence
            )
            generated_data["sections"][section_name] = narrative

        # 4. Save and store CustomReport
        custom_report = CustomReport(
            audit_id=audit_id,
            template=template,
            sections=sections,
            generated_json=generated_data,
        )
        db.add(custom_report)
        db.commit()
        db.refresh(custom_report)
        return custom_report

    async def update_custom_report(
        self,
        *,
        db: Session,
        user: User,
        report_id: str,
        generated_json: dict,
    ) -> CustomReport:
        """Update/Edit a previously generated custom report's contents."""
        custom_report = db.get(CustomReport, report_id)
        if not custom_report:
            raise ValueError("Custom report not found.")

        # Check access
        statement = select(AuditRun).where(AuditRun.id == custom_report.audit_id)
        if (user.role or "").upper() not in {"ADMIN", "REVIEWER"}:
            statement = statement.where(AuditRun.user_id == user.id)
        audit = db.scalar(statement)
        if not audit:
            raise ValueError("Access denied to parent audit report.")

        custom_report.generated_json = generated_json
        db.commit()
        db.refresh(custom_report)
        return custom_report

    async def _generate_section_narrative(
        self,
        *,
        template: str,
        section_name: str,
        audit_meta: dict,
        findings: list[Finding],
        remediations: list[RemediationPlan],
        evidence: list[EvidenceLink]
    ) -> str:
        """Use the LLM to rewrite and format a specific section with template-tailored narrative."""
        system_prompt = (
            "You are a professional compliance auditor. Generate a cohesive, polished narrative section for a compliance report in Markdown format.\n"
            "Do not include code blocks wrapping the entire output, just respond with plain Markdown text.\n"
            f"The target audience template is: '{template}'. Tailor the tone accordingly:\n"
            "- **Executive**: Concise, strategic, business risk focus, and compliance dashboard highlights. Minimize technical jargon.\n"
            "- **Auditor**: Formal, highly structured, compliance rule citations, and objective observation language.\n"
            "- **Board**: Governance focus, strategic impact, corporate risk levels, and resource investment suggestions.\n"
            "- **Technical**: Deep technical dive into configuration failures, precise codebase/policy exceptions, and developer-oriented mitigation notes.\n"
        )

        # Build context payload
        findings_context = []
        for f in findings:
            findings_context.append({
                "id": f.id,
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "status": f.status,
                "rule_id": f.rule_id,
            })

        remediation_context = []
        for r in remediations:
            remediation_context.append({
                "finding_id": r.finding_id,
                "steps": r.steps,
                "effort_hours": r.estimated_effort_hours,
                "priority": r.priority,
                "suggested_owner": r.suggested_owner_role,
            })

        evidence_context = []
        for ev in evidence:
            evidence_context.append({
                "finding_id": ev.finding_id,
                "evidence_type": ev.evidence_type,
                "excerpt": ev.evidence_excerpt,
            })

        user_prompt = (
            f"Please generate the '{section_name}' section.\n\n"
            f"Audit Metadata:\n"
            f"- Document Evaluated: {audit_meta['document_title']}\n"
            f"- Overall Risk Level: {audit_meta['overall_risk']}\n"
            f"- Compliance Rating: {audit_meta['compliance_score']}%\n"
            f"- Total Non-Compliant Items: {audit_meta['total_findings']} ({audit_meta['high_severity']} High, {audit_meta['medium_severity']} Medium, {audit_meta['low_severity']} Low)\n\n"
            f"Findings:\n{json.dumps(findings_context, indent=2)}\n\n"
            f"Remediation Plans:\n{json.dumps(remediation_context, indent=2)}\n\n"
            f"Evidence Links:\n{json.dumps(evidence_context, indent=2)}\n\n"
            f"Focus solely on the content relevant to '{section_name}'. Generate beautiful markdown."
        )

        try:
            return llm_service.generate_text(system=system_prompt, user=user_prompt)
        except Exception as exc:
            logger.error("LLM section generation failed: %s", exc)
            # Safe fallback text if LLM fails
            return (
                f"### {section_name} (Manual Fallback)\n\n"
                f"This section presents the compliance summary for document **{audit_meta['document_title']}**.\n"
                f"- Compliance Score: **{audit_meta['compliance_score']}%**\n"
                f"- Findings Count: **{audit_meta['total_findings']}**\n\n"
                f"Please edit this section directly to add customized notes."
            )

    def export_to_docx(self, report: CustomReport) -> bytes:
        """Export the custom report to a formatted Microsoft Word DOCX file."""
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor

        doc = Document()
        
        # Styles setup
        styles = doc.styles
        
        # Document Title
        title_text = report.generated_json.get("title", "Compliance Report")
        title = doc.add_paragraph()
        run = title.add_run(title_text)
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(124, 77, 255) # brand violet
        title.alignment = 0 # Left

        # Metadata table
        meta = report.generated_json.get("metadata", {})
        doc.add_paragraph(f"Generated on: {meta.get('generated_at', datetime.utcnow().isoformat())}")
        doc.add_paragraph(f"Assessment Document: {meta.get('document_title', 'N/A')}")
        doc.add_paragraph(f"Compliance Rating: {meta.get('compliance_score', 0)}% (Overall Risk: {meta.get('overall_risk', 'UNKNOWN')})")
        doc.add_paragraph("---" * 15)

        # Render sections
        sections_dict = report.generated_json.get("sections", {})
        for sec_name, sec_content in sections_dict.items():
            h = doc.add_paragraph()
            h_run = h.add_run(sec_name)
            h_run.font.size = Pt(16)
            h_run.font.bold = True
            h_run.font.color.rgb = RGBColor(0, 229, 255) # cyan
            
            # Add text
            doc.add_paragraph(sec_content)
            doc.add_paragraph("")

        # Save to buffer
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream.getvalue()

    def export_to_pdf(self, report: CustomReport) -> bytes:
        """Export the custom report to a beautifully formatted PDF file using xhtml2pdf if available."""
        # Build HTML payload
        meta = report.generated_json.get("metadata", {})
        sections_dict = report.generated_json.get("sections", {})
        
        sections_html = ""
        for sec_name, sec_content in sections_dict.items():
            # simple markdown format conversion
            formatted_content = sec_content.replace("\n", "<br/>").replace("**", "<strong>").replace("###", "<h3>").replace("##", "<h2>")
            sections_html += f"""
            <div class="section">
                <h2>{sec_name}</h2>
                <div class="content">{formatted_content}</div>
            </div>
            """

        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Helvetica', 'Arial', sans-serif;
                    color: #090A0F;
                    padding: 20px;
                }}
                h1 {{
                    color: #7C4DFF;
                    font-size: 24px;
                    border-bottom: 2px solid #7C4DFF;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #00E5FF;
                    font-size: 18px;
                    margin-top: 20px;
                }}
                .meta-box {{
                    background-color: #F5F6FA;
                    border: 1px solid #94A3B8;
                    padding: 15px;
                    margin-bottom: 30px;
                    border-radius: 5px;
                }}
                .section {{
                    margin-bottom: 20px;
                }}
                .content {{
                    font-size: 11px;
                    line-height: 1.6;
                    color: #334155;
                }}
            </style>
        </head>
        <body>
            <h1>{report.generated_json.get("title", "Compliance Report")}</h1>
            <div class="meta-box">
                <strong>Document Evaluated:</strong> {meta.get('document_title', 'N/A')}<br/>
                <strong>Overall Risk Level:</strong> {meta.get('overall_risk', 'UNKNOWN')}<br/>
                <strong>Compliance Score:</strong> {meta.get('compliance_score', 0)}%<br/>
                <strong>Generated At:</strong> {meta.get('generated_at', '')}<br/>
            </div>
            {sections_html}
        </body>
        </html>
        """

        try:
            from xhtml2pdf import pisa
            pdf_stream = io.BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_stream)
            if not pisa_status.err:
                return pdf_stream.getvalue()
            else:
                logger.error("xhtml2pdf rendering status contained errors.")
        except Exception as exc:
            logger.error("Failed to compile PDF via xhtml2pdf: %s", exc)

        # Fallback to simple manual PDF syntax if xhtml2pdf fails
        return self._fallback_pdf(report)

    def _fallback_pdf(self, report: CustomReport) -> bytes:
        """A rock-solid manual PDF byte stream compiler (no external dependency)."""
        meta = report.generated_json.get("metadata", {})
        sections_dict = report.generated_json.get("sections", {})

        lines = [
            report.generated_json.get("title", "Compliance Report"),
            f"Generated: {meta.get('generated_at', '')}",
            f"Document: {meta.get('document_title', 'N/A')}",
            f"Compliance Rating: {meta.get('compliance_score', 0)}% (Risk: {meta.get('overall_risk', 'UNKNOWN')})",
            "",
        ]
        for name, content in sections_dict.items():
            lines.append(f"--- {name} ---")
            lines.append(content[:1500]) # Cap text to avoid overflowing simple canvas layout
            lines.append("")

        full_text = "\n".join(lines)
        escaped_lines = []
        import textwrap
        for raw_line in full_text.splitlines():
            for line in textwrap.wrap(raw_line, width=90) or [""]:
                escaped_lines.append(line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)"))
        escaped_lines = escaped_lines[:55]

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

reports_service = ReportsService()

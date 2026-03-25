"""
PDF generation utilities for ContractVault.
Uses ReportLab to generate contract documents.
"""
import io
import os
import logging
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)


def _get_styles():
    """Return custom paragraph styles for contract documents."""
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ContractTitle",
            parent=styles["Title"],
            fontSize=20,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1a237e"),
        )
    )
    styles.add(
        ParagraphStyle(
            "ContractSubtitle",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#37474f"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#1a237e"),
            borderWidth=0,
            borderPadding=0,
        )
    )
    styles.add(
        ParagraphStyle(
            "ClauseText",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        )
    )
    styles.add(
        ParagraphStyle(
            "FooterText",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#616161"),
        )
    )
    styles.add(
        ParagraphStyle(
            "MetaValue",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=4,
        )
    )
    return styles


def generate_contract_pdf(contract):
    """
    Generate a PDF document for a contract.

    Args:
        contract: Contract model instance with related parties, clauses, etc.

    Returns:
        bytes: The generated PDF content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _get_styles()
    elements = []

    # Title
    elements.append(Paragraph(contract.title, styles["ContractTitle"]))
    elements.append(
        Paragraph(
            f"Contract #{contract.contract_number}",
            styles["ContractSubtitle"],
        )
    )
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a237e")))
    elements.append(Spacer(1, 20))

    # Contract metadata table
    meta_data = [
        ["Contract Type:", str(contract.contract_type) if contract.contract_type else "N/A"],
        ["Status:", contract.get_status_display()],
        ["Created:", contract.created_at.strftime("%B %d, %Y")],
        ["Effective Date:", contract.effective_date.strftime("%B %d, %Y") if contract.effective_date else "TBD"],
        ["Expiration Date:", contract.expiration_date.strftime("%B %d, %Y") if contract.expiration_date else "N/A"],
        ["Total Value:", f"${contract.total_value:,.2f}" if contract.total_value else "N/A"],
    ]

    meta_table = Table(meta_data, colWidths=[1.5 * inch, 4.5 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
                ("FONT", (1, 0), (1, -1), "Helvetica", 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#616161")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # Parties section
    parties = contract.parties.all()
    if parties.exists():
        elements.append(Paragraph("PARTIES", styles["SectionHeading"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
        elements.append(Spacer(1, 8))

        for party in parties:
            party_info = f"<b>{party.get_role_display()}:</b> {party.name}"
            if party.email:
                party_info += f" ({party.email})"
            if party.organization_name:
                party_info += f" - {party.organization_name}"
            elements.append(Paragraph(party_info, styles["ClauseText"]))
        elements.append(Spacer(1, 12))

    # Description
    if contract.description:
        elements.append(Paragraph("DESCRIPTION", styles["SectionHeading"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(contract.description, styles["ClauseText"]))
        elements.append(Spacer(1, 12))

    # Clauses
    clauses = contract.clauses.order_by("order")
    if clauses.exists():
        elements.append(Paragraph("TERMS AND CONDITIONS", styles["SectionHeading"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
        elements.append(Spacer(1, 8))

        for idx, clause in enumerate(clauses, start=1):
            clause_title = f"<b>Article {idx}: {clause.title}</b>"
            elements.append(Paragraph(clause_title, styles["ClauseText"]))
            elements.append(Paragraph(clause.content, styles["ClauseText"]))
            elements.append(Spacer(1, 6))

    # Signature block
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("SIGNATURES", styles["SectionHeading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
    elements.append(Spacer(1, 16))

    signatures = []
    if hasattr(contract, "signature_requests"):
        for sig_req in contract.signature_requests.select_related("signer").all():
            sig_data = [sig_req.signer.get_full_name() or sig_req.signer.email]
            if hasattr(sig_req, "signature") and sig_req.signature:
                sig_data.append(f"Signed: {sig_req.signature.signed_at.strftime('%B %d, %Y')}")
            else:
                sig_data.append("Pending Signature")
            signatures.append(sig_data)

    if not signatures:
        for party in parties:
            signatures.append([party.name, "________________________"])

    if signatures:
        sig_table = Table(signatures, colWidths=[3 * inch, 3 * inch])
        sig_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                    ("FONT", (1, 0), (1, -1), "Helvetica", 10),
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
                    ("LINEBELOW", (1, 0), (1, -1), 0.5, colors.black),
                ]
            )
        )
        elements.append(sig_table)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray))
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            f"Generated by ContractVault on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            styles["FooterText"],
        )
    )
    elements.append(
        Paragraph(
            "This document is electronically generated. Digital signatures are legally binding.",
            styles["FooterText"],
        )
    )

    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    return pdf_content


def save_contract_pdf(contract):
    """
    Generate and save a contract PDF to the media directory.

    Args:
        contract: Contract model instance.

    Returns:
        str: Relative path to the saved PDF file.
    """
    pdf_content = generate_contract_pdf(contract)

    relative_dir = f"contracts/pdfs/{contract.organization_id}"
    absolute_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    filename = f"contract_{contract.contract_number}_{contract.version}.pdf"
    relative_path = os.path.join(relative_dir, filename)
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    with open(absolute_path, "wb") as f:
        f.write(pdf_content)

    logger.info("Generated PDF for contract %s: %s", contract.contract_number, relative_path)
    return relative_path

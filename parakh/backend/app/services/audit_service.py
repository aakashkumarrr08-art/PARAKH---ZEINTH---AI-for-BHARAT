from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.config import get_settings
from app.models.evaluation import EvaluationEvent
from app.services.bdi_service import get_bidder
from app.services.tue_service import get_tender


async def get_audit_history(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> dict[str, list[EvaluationEvent]]:
    await get_bidder(db, tender_id, bidder_id)
    rows = await db.evaluation_events.find({"tender_id": tender_id, "bidder_id": bidder_id}).sort("sequence", 1).to_list(length=500)
    events = [EvaluationEvent(**row) for row in rows]
    grouped: dict[str, list[EvaluationEvent]] = defaultdict(list)
    for event in events:
        grouped[event.criterion_name].append(event)
    return dict(grouped)


async def export_audit_report(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str, export_format: str) -> Path:
    bidder = await get_bidder(db, tender_id, bidder_id)
    tender = await get_tender(db, tender_id)
    history = await get_audit_history(db, tender_id, bidder_id)

    settings = get_settings()
    target_dir = settings.audit_export_root / tender_id / bidder_id
    target_dir.mkdir(parents=True, exist_ok=True)

    if export_format == "pdf":
        path = target_dir / "audit_report.pdf"
        _write_pdf(path, tender.title, bidder.name, bidder.overall_status, history)
        return path
    if export_format == "xlsx":
        path = target_dir / "audit_report.xlsx"
        _write_xlsx(path, tender.title, bidder.name, bidder.overall_status, history)
        return path
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format.")


def _write_xlsx(path: Path, tender_title: str, bidder_name: str, overall_status: str, history: dict[str, list[EvaluationEvent]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Appendix B Audit"
    sheet.append(["Tender", tender_title])
    sheet.append(["Bidder", bidder_name])
    sheet.append(["Overall Status", overall_status])
    sheet.append([])
    sheet.append(
        [
            "Criterion",
            "Stage",
            "Event Type",
            "Auto Verdict",
            "Final Verdict",
            "Evidence Quality",
            "Reason Code",
            "Match Logic",
            "Evidence Docs",
            "Event Hash",
            "Prior Event",
        ]
    )
    for criterion_name, events in history.items():
        for event in events:
            sheet.append(
                [
                    criterion_name,
                    event.stage,
                    event.event_type,
                    event.auto_verdict,
                    event.final_verdict,
                    event.evidence_quality,
                    event.reason_code,
                    event.match_logic,
                    ", ".join(f"{doc.doc_name} ({doc.filename})" for doc in event.evidence_docs),
                    event.event_hash,
                    event.prior_event_id,
                ]
            )
    workbook.save(path)


def _write_pdf(path: Path, tender_title: str, bidder_name: str, overall_status: str, history: dict[str, list[EvaluationEvent]]) -> None:
    document = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph("PARAKH Audit Report", styles["Title"]),
        Paragraph(f"Tender: {tender_title}", styles["BodyText"]),
        Paragraph(f"Bidder: {bidder_name}", styles["BodyText"]),
        Paragraph(f"Overall Status: {overall_status}", styles["BodyText"]),
        Spacer(1, 12),
    ]

    table_data = [["Criterion", "Event", "Final Verdict", "Evidence", "Logic"]]
    for criterion_name, events in history.items():
        for event in events:
            table_data.append(
                [
                    criterion_name,
                    event.event_type,
                    event.final_verdict,
                    ", ".join(doc.filename for doc in event.evidence_docs) or "-",
                    event.match_logic[:1200],
                ]
            )
    table = Table(table_data, repeatRows=1, colWidths=[100, 60, 80, 120, 180])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9bb0c3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    document.build(story)


async def get_dashboard_stats(db: AsyncIOMotorDatabase) -> dict[str, int]:
    total_tenders = await db.tenders.count_documents({})
    total_bidders = await db.bidders.count_documents({})
    total_disqualified = await db.bidders.count_documents({"hard_disqualified": True})
    total_events = await db.evaluation_events.count_documents({})
    total_overrides = await db.evaluation_events.count_documents({"event_type": "OVERRIDE"})
    auto_resolved = await db.evaluation_events.count_documents(
        {"event_type": "AUTO_EVAL", "final_verdict": {"$in": ["Eligible", "Not Eligible"]}}
    )
    return {
        "tenders": total_tenders,
        "bidders": total_bidders,
        "disqualifications": total_disqualified,
        "evaluation_events": total_events,
        "manual_overrides": total_overrides,
        "auto_resolved": auto_resolved,
    }

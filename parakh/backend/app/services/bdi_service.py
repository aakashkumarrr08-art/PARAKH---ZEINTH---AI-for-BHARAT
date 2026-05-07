from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from statistics import mean

from fastapi import HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.ml.boq_extraction import extract_quantities
from app.ml.ocr_pipeline import extract_text
from app.models.bidder import Bidder, BidderCreate, BidderDocument, ChecklistStatusItem
from app.models.common import generate_id, mongo_compatible, utcnow
from app.models.evidence import ExtractedEvidence, ExtractedField
from app.services.tue_service import checklist_template


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_number(raw: str) -> float:
    return float(raw.replace(",", "").strip())


def _extract_amounts_lakh(text: str) -> list[float]:
    matches = re.findall(r"(?:rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakhs?|l)\b", text, re.IGNORECASE)
    values: list[float] = []
    for raw_number, unit in matches:
        amount = _clean_number(raw_number)
        if unit.lower().startswith(("crore", "cr")):
            values.append(round(amount * 100, 2))
        else:
            values.append(round(amount, 2))
    return values


def _extract_date(text: str) -> str | None:
    match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
    if match:
        raw = match.group(1).replace("-", "/")
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _presence_field(name: str, present: bool, confidence: float, snippet: str) -> ExtractedField:
    return ExtractedField(name=name, value=present, confidence=confidence, source_text=snippet[:240], page_numbers=[])


def _numeric_field(name: str, value, confidence: float, snippet: str) -> ExtractedField:
    return ExtractedField(name=name, value=value, confidence=confidence, source_text=snippet[:240], page_numbers=[])


def _extract_for_document(doc_name: str, filename: str, text: str) -> list[ExtractedField]:
    lowered = text.lower()
    fields: list[ExtractedField] = []

    if doc_name == "EMD Proof" or "emd" in filename.lower():
        amount = None
        if re.search(r"2,75,00,000|27500000|2\.75\s*crore", lowered):
            amount = 27500000
        else:
            amount_matches = re.findall(r"(?:rs\.?|inr)?\s*([\d,]+)", text, re.IGNORECASE)
            if amount_matches:
                amount = int(_clean_number(amount_matches[0]))
        validity = _extract_date(text)
        fields.extend(
            [
                _numeric_field("emd_amount_inr", amount, 0.92 if amount else 0.35, text),
                _numeric_field("emd_validity_date", validity, 0.86 if validity else 0.3, text),
                _numeric_field(
                    "emd_instrument_type",
                    "bank_guarantee" if "bank guarantee" in lowered else ("deposit" if "deposit" in lowered else None),
                    0.82 if ("bank guarantee" in lowered or "deposit" in lowered) else 0.3,
                    text,
                ),
            ]
        )

    if doc_name == "Industrial License" or "license" in filename.lower():
        fields.extend(
            [
                _presence_field("industrial_license_present", "industrial license" in lowered or "license" in lowered, 0.9 if "license" in lowered else 0.25, text),
                _numeric_field("dpiit_reference", "DPIIT" if "dpiit" in lowered or "dipp" in lowered else None, 0.78 if ("dpiit" in lowered or "dipp" in lowered) else 0.25, text),
                _presence_field("br_jacket_scope", "br jacket" in lowered or "bullet resistant jacket" in lowered, 0.84 if ("br jacket" in lowered or "bullet resistant jacket" in lowered) else 0.3, text),
            ]
        )

    if doc_name == "Ballistic Test Reports" or "ballistic" in filename.lower():
        levels = [int(value) for value in re.findall(r"level[\s-]*(\d+)", lowered)]
        panel_text = lowered
        front = max(levels) if "front" in panel_text and levels else None
        back = max(levels) if "back" in panel_text and levels else None
        side = max(levels) if "side" in panel_text and levels else None
        if front is None and levels:
            front = levels[0]
        if back is None and len(levels) > 1:
            back = levels[min(1, len(levels) - 1)]
        if side is None and len(levels) > 2:
            side = levels[min(2, len(levels) - 1)]
        fields.extend(
            [
                _numeric_field("ballistic_front_level", front, 0.88 if front else 0.3, text),
                _numeric_field("ballistic_back_level", back, 0.88 if back else 0.3, text),
                _numeric_field("ballistic_side_level", side, 0.88 if side else 0.3, text),
            ]
        )

    if doc_name == "Technical Compliance" or "technical_compliance" in filename.lower() or "compliance" in filename.lower():
        sizes = extract_quantities(text)
        pattern_deviation = any(keyword in lowered for keyword in ["deviation", "alternate pattern", "not comply"])
        fields.extend(
            [
                _presence_field("camouflage_pattern_mentioned", "camouflage" in lowered, 0.85 if "camouflage" in lowered else 0.3, text),
                _presence_field("pattern_deviation_flag", pattern_deviation, 0.74 if pattern_deviation else 0.68, text),
                _numeric_field("size_m", sizes.get("size_m"), 0.9 if sizes.get("size_m") else 0.28, text),
                _numeric_field("size_l", sizes.get("size_l"), 0.9 if sizes.get("size_l") else 0.28, text),
                _numeric_field("size_xl", sizes.get("size_xl"), 0.9 if sizes.get("size_xl") else 0.28, text),
            ]
        )

    if doc_name == "Annual Turnover Certificate" or "turnover" in filename.lower():
        amounts = _extract_amounts_lakh(text)
        bidder_values = amounts[:3]
        oem_values = amounts[3:6]
        fields.extend(
            [
                _numeric_field("bidder_turnover_values_lakh", bidder_values, 0.8 if bidder_values else 0.25, text),
                _numeric_field("oem_turnover_values_lakh", oem_values, 0.74 if oem_values else 0.2, text),
                _numeric_field("bidder_turnover_avg_lakh", round(mean(bidder_values), 2) if bidder_values else None, 0.82 if bidder_values else 0.25, text),
                _numeric_field("oem_turnover_avg_lakh", round(mean(oem_values), 2) if oem_values else None, 0.76 if oem_values else 0.25, text),
            ]
        )

    if doc_name == "Past Performance Records" or "performance" in filename.lower():
        quantity_matches = [int(raw.replace(",", "")) for raw in re.findall(r"(\d[\d,]*)\s*(?:units|jackets|nos)", lowered)]
        level_matches = [int(raw) for raw in re.findall(r"level[\s-]*(\d+)", lowered)]
        fields.extend(
            [
                _numeric_field("max_supply_units", max(quantity_matches) if quantity_matches else None, 0.78 if quantity_matches else 0.3, text),
                _numeric_field("max_supply_level", max(level_matches) if level_matches else None, 0.82 if level_matches else 0.3, text),
            ]
        )

    if doc_name == "OEM Authorization" or "oem" in filename.lower() or "authoriz" in filename.lower():
        fields.append(
            _presence_field("oem_authorization_present", "authoriz" in lowered, 0.88 if "authoriz" in lowered else 0.25, text)
        )

    if doc_name == "PAN and TIN Certificates" or "pan" in filename.lower() or "tin" in filename.lower() or "gst" in filename.lower():
        pan_match = re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text)
        gstin_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b", text)
        tin_present = "tin" in lowered or bool(re.search(r"\b\d{11}\b", text))
        fields.extend(
            [
                _presence_field("pan_present", pan_match is not None or "pan" in lowered, 0.9 if (pan_match or "pan" in lowered) else 0.2, text),
                _presence_field("tin_present", tin_present, 0.82 if tin_present else 0.25, text),
                _numeric_field("gstin", gstin_match.group(0) if gstin_match else None, 0.92 if gstin_match else 0.2, text),
            ]
        )

    if doc_name == "Proof of Experience" or "experience" in filename.lower():
        years_match = re.search(r"(\d+)\s+years", lowered)
        fields.append(
            _numeric_field("experience_years", int(years_match.group(1)) if years_match else None, 0.82 if years_match else 0.25, text)
        )

    if not fields:
        fields.append(_numeric_field("document_text_present", bool(text), 0.6 if text else 0.1, text))

    return fields


async def register_bidder(db: AsyncIOMotorDatabase, tender_id: str, payload: BidderCreate) -> Bidder:
    bidder = Bidder(
        tender_id=tender_id,
        name=payload.name,
        bidder_type=payload.bidder_type,
        oem_name=payload.oem_name,
        checklist_status=checklist_template(),
        overall_status="PENDING",
    )
    await db.bidders.insert_one(mongo_compatible(bidder))
    return bidder


async def list_bidders(db: AsyncIOMotorDatabase, tender_id: str) -> list[Bidder]:
    rows = await db.bidders.find({"tender_id": tender_id}).sort("created_at", -1).to_list(length=200)
    return [Bidder(**row) for row in rows]


async def get_bidder(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> Bidder:
    row = await db.bidders.find_one({"_id": bidder_id, "tender_id": tender_id})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bidder not found.")
    return Bidder(**row)


async def upload_bidder_document(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    bidder_id: str,
    doc_name: str,
    file: UploadFile,
) -> Bidder:
    bidder = await get_bidder(db, tender_id, bidder_id)
    settings = get_settings()
    document_id = generate_id()
    extension = Path(file.filename or "upload.pdf").suffix
    target_dir = settings.upload_root / "bidders" / tender_id / bidder_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document_id}{extension}"
    target_path.write_bytes(await file.read())

    document = BidderDocument(
        document_id=document_id,
        filename=file.filename or target_path.name,
        doc_name=doc_name,
        relative_path=f"/uploads/bidders/{tender_id}/{bidder_id}/{target_path.name}",
        content_type=file.content_type,
        uploaded_at=_iso_now(),
    )
    bidder.documents.append(document)

    refreshed_status: list[ChecklistStatusItem] = []
    for item in bidder.checklist_status:
        if item.doc_name == doc_name:
            refreshed_status.append(
                ChecklistStatusItem(
                    doc_name=item.doc_name,
                    doc_description=item.doc_description,
                    doc_purpose=item.doc_purpose,
                    uploaded=True,
                    document_id=document.document_id,
                    filename=document.filename,
                )
            )
        else:
            refreshed_status.append(item)
    bidder.checklist_status = refreshed_status
    bidder.updated_at = utcnow()

    await db.bidders.update_one(
        {"_id": bidder_id},
        {
            "$set": {
                "documents": [doc.model_dump() for doc in bidder.documents],
                "checklist_status": [item.model_dump() for item in bidder.checklist_status],
                "updated_at": bidder.updated_at,
            }
        },
    )
    return bidder


async def ingest_bidder_documents(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> list[ExtractedEvidence]:
    bidder = await get_bidder(db, tender_id, bidder_id)
    evidences: list[ExtractedEvidence] = []

    for document in bidder.documents:
        settings = get_settings()
        absolute_path = settings.upload_root.parent / document.relative_path.strip("/")
        text, method, base_confidence = extract_text(str(absolute_path))
        fields = _extract_for_document(document.doc_name, document.filename, text)
        overall_confidence = round(mean([field.confidence for field in fields] + [base_confidence]), 3)
        evidence = ExtractedEvidence(
            tender_id=tender_id,
            bidder_id=bidder_id,
            document_id=document.document_id,
            doc_name=document.doc_name,
            filename=document.filename,
            relative_path=document.relative_path,
            extraction_method=method,
            text_preview=text[:1500],
            fields=fields,
            overall_confidence=overall_confidence,
        )
        evidences.append(evidence)
        await db.extracted_evidence.replace_one(
            {"tender_id": tender_id, "bidder_id": bidder_id, "document_id": document.document_id},
            mongo_compatible(evidence),
            upsert=True,
        )

    await db.bidders.update_one(
        {"_id": bidder_id},
        {"$set": {"updated_at": utcnow()}},
    )
    return evidences


async def get_bidder_checklist(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> list[ChecklistStatusItem]:
    bidder = await get_bidder(db, tender_id, bidder_id)
    return bidder.checklist_status


async def get_extracted_evidence(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> list[ExtractedEvidence]:
    rows = await db.extracted_evidence.find({"tender_id": tender_id, "bidder_id": bidder_id}).sort("created_at", -1).to_list(length=200)
    return [ExtractedEvidence(**row) for row in rows]

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.core.policy_loader import load_bidder_doc_checklist, load_evaluation_criteria
from app.models.bidder import ChecklistStatusItem
from app.models.common import generate_id, mongo_compatible, utcnow
from app.models.manifest import CriteriaManifestVersion, Criterion, EvidenceTemplate
from app.models.tender import ManifestUpdateRequest, Tender, TenderCreate, TenderDocument


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checklist_lookup() -> dict[str, dict[str, str]]:
    return {row["doc_name"]: row for row in load_bidder_doc_checklist()}


def _criterion_to_evidence(factor: str, checklist: dict[str, dict[str, str]]) -> list[EvidenceTemplate]:
    mapping = {
        "EMD Validity": [
            ("EMD Proof", ["emd_amount_inr", "emd_validity_date", "emd_instrument_type"]),
        ],
        "Legal Standing": [
            ("Industrial License", ["industrial_license_present", "dpiit_reference", "br_jacket_scope"]),
            ("PAN and TIN Certificates", ["pan_present", "tin_present", "gstin"]),
        ],
        "Protection Level": [
            ("Ballistic Test Reports", ["ballistic_front_level", "ballistic_back_level", "ballistic_side_level"]),
        ],
        "Design/Pattern": [
            ("Technical Compliance", ["camouflage_pattern_mentioned", "pattern_deviation_flag"]),
        ],
        "Sizing Accuracy": [
            ("Technical Compliance", ["size_m", "size_l", "size_xl"]),
        ],
        "Turnover Depth": [
            ("Annual Turnover Certificate", ["bidder_turnover_values_lakh", "oem_turnover_values_lakh"]),
        ],
        "Supply History": [
            ("Past Performance Records", ["max_supply_units", "max_supply_level"]),
            ("Proof of Experience", ["experience_years"]),
        ],
    }
    templates: list[EvidenceTemplate] = []
    for doc_name, fields in mapping.get(factor, []):
        doc = checklist.get(doc_name, {})
        templates.append(
            EvidenceTemplate(
                doc_name=doc_name,
                doc_description=doc.get("doc_description"),
                required_fields=fields,
                required=True,
            )
        )
    return templates


def _build_criterion(row: dict[str, str]) -> Criterion:
    checklist = _checklist_lookup()
    factor = row["Factor"].strip()
    description = row["DescriptionMetric"].strip()

    if factor == "EMD Validity":
        criterion_type = "emd_rule"
        classification = "hard"
        threshold = {"amount_inr": 27500000, "validity_days_beyond_bid": 45}
        notes = "Strict numeric and date validation. Any missing proof still routes to manual review."
    elif factor == "Legal Standing":
        criterion_type = "certification_presence"
        classification = "hard"
        threshold = {"industrial_license_required": True, "pan_required": True, "tin_required": True}
        notes = "Industrial license must be for BR Jackets, with PAN/TIN evidence."
    elif factor == "Protection Level":
        criterion_type = "ballistic_level"
        classification = "hard"
        threshold = {"front_min_level": 6, "back_min_level": 6, "side_min_level": 6, "standard": "IS 17051"}
        notes = "Any panel below Level-6 is a hard disqualification trigger."
    elif factor == "Design/Pattern":
        criterion_type = "pattern_compliance"
        classification = "graduated"
        threshold = {"required_pattern": "CRPF Digital Camouflage"}
        notes = "Subjective design fit; always escalates to officer workbench for confirmation."
    elif factor == "Sizing Accuracy":
        criterion_type = "quantity_capacity"
        classification = "hard"
        threshold = {"size_m": 1000, "size_l": 3000, "size_xl": 1000}
        notes = "Structured quantity check against GSQR size mix."
    elif factor == "Turnover Depth":
        criterion_type = "financial_threshold"
        classification = "hard"
        threshold = {
            "bidder_avg_turnover_lakh": 500,
            "oem_avg_turnover_lakh": 1000,
            "years": 3,
        }
        notes = "No tolerance. Even a 1 lakh shortfall triggers the financial disqualification rule."
    else:
        criterion_type = "similar_work_history"
        classification = "graduated"
        threshold = {"min_units": 1500, "min_level": 5, "lookback_years": 3}
        notes = "Quantities can be extracted, but similarity and comparability stay officer-reviewed."

    return Criterion(
        criterion_id=_slugify(factor),
        stage=row["Stage"].strip(),
        factor=factor,
        description=description,
        type=criterion_type,
        classification=classification,
        mandatory=True,
        normalized_threshold=threshold,
        evidence_template=_criterion_to_evidence(factor, checklist),
        guidance_notes=notes,
    )


async def list_tenders(db: AsyncIOMotorDatabase) -> list[Tender]:
    rows = await db.tenders.find({}).sort("created_at", -1).to_list(length=200)
    return [Tender(**row) for row in rows]


async def get_tender(db: AsyncIOMotorDatabase, tender_id: str) -> Tender:
    row = await db.tenders.find_one({"_id": tender_id})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found.")
    return Tender(**row)


async def create_tender(db: AsyncIOMotorDatabase, payload: TenderCreate, created_by: str) -> Tender:
    tender = Tender(
        title=payload.title,
        procuring_entity=payload.procuring_entity,
        bid_reference=payload.bid_reference,
        description=payload.description,
        bid_validity_end=payload.bid_validity_end,
        status="ACTIVE",
        created_by=created_by,
    )
    await db.tenders.insert_one(mongo_compatible(tender))
    return tender


async def upload_tender_document(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    doc_type: str,
    file: UploadFile,
) -> Tender:
    tender = await get_tender(db, tender_id)
    settings = get_settings()
    document_id = generate_id()
    extension = Path(file.filename or "upload.pdf").suffix
    target_dir = settings.upload_root / "tenders" / tender_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document_id}{extension}"
    target_path.write_bytes(await file.read())

    relative_path = f"/uploads/tenders/{tender_id}/{target_path.name}"
    document = TenderDocument(
        document_id=document_id,
        filename=file.filename or target_path.name,
        doc_type=doc_type,
        relative_path=relative_path,
        uploaded_at=_iso_now(),
    )
    tender.documents.append(document)
    tender.updated_at = utcnow()
    await db.tenders.update_one(
        {"_id": tender_id},
        {"$set": {"documents": [item.model_dump() for item in tender.documents], "updated_at": tender.updated_at}},
    )
    return tender


async def _next_manifest_version(db: AsyncIOMotorDatabase, tender_id: str) -> int:
    latest = await db.criteria_manifest_versions.find_one({"tender_id": tender_id}, sort=[("version", -1)])
    return (latest or {}).get("version", 0) + 1


async def generate_manifest(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    generated_by: str,
) -> CriteriaManifestVersion:
    tender = await get_tender(db, tender_id)
    criteria = [_build_criterion(row) for row in load_evaluation_criteria()]
    version = await _next_manifest_version(db, tender_id)
    manifest = CriteriaManifestVersion(
        tender_id=tender_id,
        version=version,
        status="DRAFT",
        source_documents=[item.document_id for item in tender.documents],
        criteria=criteria,
    )
    await db.criteria_manifest_versions.insert_one(mongo_compatible(manifest))
    await db.tenders.update_one(
        {"_id": tender_id},
        {"$set": {"latest_manifest_id": manifest.id, "updated_at": utcnow()}},
    )
    return manifest


async def get_latest_manifest(db: AsyncIOMotorDatabase, tender_id: str) -> CriteriaManifestVersion:
    row = await db.criteria_manifest_versions.find_one({"tender_id": tender_id}, sort=[("version", -1)])
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found.")
    return CriteriaManifestVersion(**row)


async def get_latest_approved_manifest(db: AsyncIOMotorDatabase, tender_id: str) -> CriteriaManifestVersion:
    row = await db.criteria_manifest_versions.find_one(
        {"tender_id": tender_id, "status": "APPROVED"},
        sort=[("version", -1)],
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No approved manifest found for this tender.")
    return CriteriaManifestVersion(**row)


async def update_manifest(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    manifest_id: str,
    payload: ManifestUpdateRequest,
) -> CriteriaManifestVersion:
    row = await db.criteria_manifest_versions.find_one({"_id": manifest_id, "tender_id": tender_id})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found.")
    manifest = CriteriaManifestVersion(**row)
    if manifest.status != "DRAFT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft manifests can be edited.")
    manifest.criteria = [Criterion(**criterion) for criterion in payload.criteria]
    manifest.updated_at = utcnow()
    await db.criteria_manifest_versions.update_one(
        {"_id": manifest_id},
        {"$set": {"criteria": [criterion.model_dump() for criterion in manifest.criteria], "updated_at": manifest.updated_at}},
    )
    return manifest


async def approve_manifest(db: AsyncIOMotorDatabase, tender_id: str, manifest_id: str, approved_by: str) -> CriteriaManifestVersion:
    row = await db.criteria_manifest_versions.find_one({"_id": manifest_id, "tender_id": tender_id})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found.")
    manifest = CriteriaManifestVersion(**row)
    await db.criteria_manifest_versions.update_many(
        {"tender_id": tender_id, "status": "APPROVED"},
        {"$set": {"status": "SUPERSEDED", "updated_at": utcnow()}},
    )
    manifest.status = "APPROVED"
    manifest.approved_at = _iso_now()
    manifest.approved_by = approved_by
    manifest.updated_at = utcnow()
    await db.criteria_manifest_versions.update_one(
        {"_id": manifest_id},
        {
            "$set": {
                "status": manifest.status,
                "approved_at": manifest.approved_at,
                "approved_by": manifest.approved_by,
                "updated_at": manifest.updated_at,
            }
        },
    )
    return manifest


async def ensure_sample_tender(db: AsyncIOMotorDatabase) -> None:
    existing = await db.tenders.find_one({"bid_reference": "CRPF-BPJ-SAMPLE-001"})
    if existing:
        tender = Tender(**existing)
    else:
        tender = Tender(
            title="CRPF Bullet Resistant Jackets Procurement",
            procuring_entity="Central Reserve Police Force",
            bid_reference="CRPF-BPJ-SAMPLE-001",
            description="Seed tender for PARAKH prototype demonstration.",
            bid_validity_end=date(2026, 9, 30),
            status="ACTIVE",
            created_by="system",
        )
        await db.tenders.insert_one(mongo_compatible(tender))

    approved_manifest = await db.criteria_manifest_versions.find_one(
        {"tender_id": tender.id, "status": "APPROVED"},
        sort=[("version", -1)],
    )
    if approved_manifest:
        await db.tenders.update_one({"_id": tender.id}, {"$set": {"latest_manifest_id": approved_manifest["_id"]}})
        return

    latest_manifest = await db.criteria_manifest_versions.find_one(
        {"tender_id": tender.id},
        sort=[("version", -1)],
    )

    if latest_manifest:
        latest_manifest_model = CriteriaManifestVersion(**latest_manifest)
        latest_manifest_model.status = "APPROVED"
        latest_manifest_model.approved_at = _iso_now()
        latest_manifest_model.approved_by = "system"
        latest_manifest_model.updated_at = utcnow()
        await db.criteria_manifest_versions.update_one(
            {"_id": latest_manifest_model.id},
            {
                "$set": {
                    "status": latest_manifest_model.status,
                    "approved_at": latest_manifest_model.approved_at,
                    "approved_by": latest_manifest_model.approved_by,
                    "updated_at": latest_manifest_model.updated_at,
                }
            },
        )
        await db.tenders.update_one({"_id": tender.id}, {"$set": {"latest_manifest_id": latest_manifest_model.id}})
        return

    manifest = CriteriaManifestVersion(
        tender_id=tender.id,
        version=1,
        status="APPROVED",
        source_documents=[],
        criteria=[_build_criterion(row) for row in load_evaluation_criteria()],
        approved_at=_iso_now(),
        approved_by="system",
    )
    await db.criteria_manifest_versions.insert_one(mongo_compatible(manifest))
    await db.tenders.update_one({"_id": tender.id}, {"$set": {"latest_manifest_id": manifest.id}})


def checklist_template() -> list[ChecklistStatusItem]:
    return [
        ChecklistStatusItem(
            doc_name=row["doc_name"],
            doc_description=row["doc_description"],
            doc_purpose=row["doc_purpose"],
        )
        for row in load_bidder_doc_checklist()
    ]

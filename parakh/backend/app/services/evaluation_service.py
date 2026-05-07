from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.policy_loader import load_policy
from app.models.common import generate_id, mongo_compatible, utcnow
from app.models.evaluation import EvaluationEvent, EvaluationOverview, EvidenceDocRef, OverrideRequest
from app.models.evidence import ExtractedEvidence, ExtractedField
from app.models.manifest import Criterion
from app.models.user import User
from app.services.bdi_service import get_bidder, get_extracted_evidence
from app.services.tue_service import get_latest_approved_manifest, get_tender


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _group_evidence(evidences: list[ExtractedEvidence]) -> tuple[dict[str, list[ExtractedEvidence]], dict[str, list[tuple[ExtractedField, ExtractedEvidence]]]]:
    docs_by_name: dict[str, list[ExtractedEvidence]] = defaultdict(list)
    fields_by_name: dict[str, list[tuple[ExtractedField, ExtractedEvidence]]] = defaultdict(list)
    for evidence in evidences:
        docs_by_name[evidence.doc_name].append(evidence)
        for field in evidence.fields:
            fields_by_name[field.name].append((field, evidence))
    return docs_by_name, fields_by_name


def _best_field(fields_by_name: dict[str, list[tuple[ExtractedField, ExtractedEvidence]]], field_name: str) -> tuple[ExtractedField | None, ExtractedEvidence | None]:
    options = fields_by_name.get(field_name, [])
    if not options:
        return None, None
    field, evidence = sorted(options, key=lambda item: item[0].confidence, reverse=True)[0]
    return field, evidence


def _required_docs_present(criterion: Criterion, docs_by_name: dict[str, list[ExtractedEvidence]]) -> tuple[list[EvidenceDocRef], list[str]]:
    docs: list[EvidenceDocRef] = []
    missing: list[str] = []
    for template in criterion.evidence_template:
        candidates = docs_by_name.get(template.doc_name, [])
        if not candidates and template.required:
            missing.append(template.doc_name)
            continue
        for evidence in candidates:
            docs.append(
                EvidenceDocRef(
                    document_id=evidence.document_id,
                    doc_name=evidence.doc_name,
                    filename=evidence.filename,
                    relative_path=evidence.relative_path,
                )
            )
    return docs, missing


def _hash_event(payload: dict[str, Any], prior_hash: str | None) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f"{prior_hash or ''}:{serialized}".encode("utf-8")).hexdigest()


async def _next_sequence_and_prior(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> tuple[int, str | None, str | None]:
    previous = await db.evaluation_events.find_one(
        {"tender_id": tender_id, "bidder_id": bidder_id},
        sort=[("sequence", -1)],
    )
    if not previous:
        return 1, None, None
    return int(previous["sequence"]) + 1, previous["_id"], previous.get("event_hash")


def _low_evidence_reason(missing_docs: list[str], low_fields: list[str]) -> str:
    parts: list[str] = []
    if missing_docs:
        parts.append(f"missing required docs: {', '.join(missing_docs)}")
    if low_fields:
        parts.append(f"low-confidence fields: {', '.join(low_fields)}")
    return "; ".join(parts)


def _evaluate_hard_rule(criterion: Criterion, tender_bid_validity_end: date | None, fields_by_name, policy: dict[str, Any]) -> tuple[str, str, dict[str, Any], list[str], str]:
    tolerances = policy["evaluation"]["tolerances"]
    extracted_values: dict[str, Any] = {}
    flags: list[str] = []

    def pull(name: str):
        field, _ = _best_field(fields_by_name, name)
        if field:
            extracted_values[name] = field.value
            return field
        extracted_values[name] = None
        return None

    if criterion.type == "emd_rule":
        amount = pull("emd_amount_inr")
        validity = pull("emd_validity_date")
        validity_date = _parse_date(validity.value if validity else None)
        required_amount = criterion.normalized_threshold["amount_inr"]
        if amount and amount.value == required_amount and validity_date and tender_bid_validity_end:
            delta = (validity_date - tender_bid_validity_end).days
            extracted_values["validity_days_beyond_bid"] = delta
            if delta >= tolerances["emd_validity_days_beyond_bid"]:
                return "Eligible", f"EMD amount matched Rs. {required_amount:,}; validity exceeded bid date by {delta} days.", extracted_values, flags, "HIGH"
            return "Not Eligible", f"EMD amount matched but validity only exceeded bid validity by {delta} days.", extracted_values, flags, "HIGH"
        if amount and amount.value is not None and amount.value != required_amount:
            flags.append("Commercial: EMD amount less than Rs. 2.75 Crores or submitted in an unapproved format.")
            return "Not Eligible", f"EMD amount {amount.value} did not match required {required_amount}.", extracted_values, flags, "HIGH"
        return "Needs Manual Review", "EMD amount/date evidence incomplete for deterministic validation.", extracted_values, flags, "LOW"

    if criterion.type == "certification_presence":
        license_present = pull("industrial_license_present")
        scope_present = pull("br_jacket_scope")
        pan_present = pull("pan_present")
        tin_present = pull("tin_present")
        if all(field and field.value for field in [license_present, scope_present, pan_present, tin_present]):
            return "Eligible", "Industrial license, BR Jacket scope, PAN, and TIN evidence were all present.", extracted_values, flags, "HIGH"
        if license_present and license_present.value is False:
            flags.append("Legal: Lack of a valid Industrial License from DPIIT specifically for BR Jackets.")
        return "Not Eligible", "One or more mandatory legal standing elements were not confirmed.", extracted_values, flags, "HIGH"

    if criterion.type == "ballistic_level":
        front = pull("ballistic_front_level")
        back = pull("ballistic_back_level")
        side = pull("ballistic_side_level")
        levels = [front.value if front else None, back.value if back else None, side.value if side else None]
        if all(level is not None for level in levels):
            if min(levels) >= tolerances["ballistic_floor_level"]:
                return "Eligible", f"All extracted ballistic panel levels met or exceeded Level-{tolerances['ballistic_floor_level']}.", extracted_values, flags, "HIGH"
            flags.append("Ballistic: Submission of test reports for any panel below BIS Level-6 (e.g., Level-5 or 4).")
            return "Not Eligible", f"At least one ballistic panel was below Level-{tolerances['ballistic_floor_level']}.", extracted_values, flags, "HIGH"
        return "Needs Manual Review", "Ballistic panel evidence was incomplete or ambiguous.", extracted_values, flags, "LOW"

    if criterion.type == "quantity_capacity":
        size_m = pull("size_m")
        size_l = pull("size_l")
        size_xl = pull("size_xl")
        expected = criterion.normalized_threshold
        if size_m and size_l and size_xl and all(value is not None for value in [size_m.value, size_l.value, size_xl.value]):
            if size_m.value == expected["size_m"] and size_l.value == expected["size_l"] and size_xl.value == expected["size_xl"]:
                return "Eligible", "Extracted size mix exactly matched 1000 (M), 3000 (L), 1000 (XL).", extracted_values, flags, "HIGH"
            return "Not Eligible", "Extracted size mix did not match the tender's required distribution.", extracted_values, flags, "HIGH"
        return "Needs Manual Review", "Sizing evidence was incomplete or low-confidence.", extracted_values, flags, "LOW"

    if criterion.type == "financial_threshold":
        bidder_avg = pull("bidder_turnover_avg_lakh")
        oem_avg = pull("oem_turnover_avg_lakh")
        bidder_threshold = criterion.normalized_threshold["bidder_avg_turnover_lakh"]
        oem_threshold = criterion.normalized_threshold["oem_avg_turnover_lakh"]
        if bidder_avg and oem_avg and bidder_avg.value is not None and oem_avg.value is not None:
            if bidder_avg.value >= bidder_threshold and oem_avg.value >= oem_threshold:
                return "Eligible", f"Bidder average turnover {bidder_avg.value}L and OEM average {oem_avg.value}L met thresholds.", extracted_values, flags, "HIGH"
            flags.append("Financial: Any shortfall in the average annual turnover (even by 1 Lakh).")
            return "Not Eligible", f"Turnover averages were below the required thresholds of {bidder_threshold}L and {oem_threshold}L.", extracted_values, flags, "HIGH"
        return "Needs Manual Review", "Turnover evidence did not support deterministic averaging.", extracted_values, flags, "LOW"

    if criterion.type == "similar_work_history":
        units = pull("max_supply_units")
        level = pull("max_supply_level")
        experience_years = pull("experience_years")
        details = []
        if units and units.value is not None:
            details.append(f"max extracted supply units={units.value}")
        if level and level.value is not None:
            details.append(f"max extracted threat level={level.value}")
        if experience_years and experience_years.value is not None:
            details.append(f"experience years={experience_years.value}")
        if level and level.value is not None and level.value < policy["evaluation"]["tolerances"]["supply_history_min_level"]:
            flags.append("Experience: Submitting past performance records for non-ballistic or low-threat (Below Level-5) items.")
        return "Needs Manual Review", " ; ".join(details) or "Supply-history comparability requires officer review.", extracted_values, flags, "HIGH" if details else "LOW"

    if criterion.type == "pattern_compliance":
        deviation = pull("pattern_deviation_flag")
        pattern = pull("camouflage_pattern_mentioned")
        if deviation and deviation.value:
            flags.append("Technical: Deviations from the specified CRPF Digital Camouflage pattern or material specs.")
        return "Needs Manual Review", "Pattern and material compliance remain officer-reviewed even when extracted hints exist.", extracted_values, flags, "HIGH" if pattern else "LOW"

    return "Needs Manual Review", "Criterion type not implemented.", extracted_values, flags, "LOW"


def _latest_by_criterion(events: list[EvaluationEvent]) -> list[EvaluationEvent]:
    latest: dict[str, EvaluationEvent] = {}
    for event in sorted(events, key=lambda item: item.sequence):
        latest[event.criterion_id] = event
    return list(latest.values())


def _compute_overall_status(events: list[EvaluationEvent], hard_disqualified: bool) -> tuple[str, list[str]]:
    reasons = [reason for event in events for reason in event.hard_disqualification_flags]
    reasons.extend([f"{event.criterion_name}: {event.match_logic}" for event in events if event.final_verdict == "Not Eligible"])
    unique_reasons = list(dict.fromkeys(reasons))

    if hard_disqualified:
        return "DISQUALIFIED", unique_reasons
    if any(event.final_verdict == "Not Eligible" for event in events):
        return "DISQUALIFIED", unique_reasons
    if any(event.final_verdict == "Needs Manual Review" for event in events):
        return "UNDER_REVIEW", unique_reasons
    return "OK", unique_reasons


def _extra_bidder_level_reasons(bidder, fields_by_name) -> list[str]:
    reasons: list[str] = []
    if bidder.bidder_type != "OEM":
        oem_auth_field, _ = _best_field(fields_by_name, "oem_authorization_present")
        if not oem_auth_field or not oem_auth_field.value:
            reasons.append("Administrative: Failure to provide a signed Manufacturer Authorization Form (MAF) if the bidder is not the OEM.")
    return reasons


async def evaluate_bidder(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    bidder_id: str,
) -> EvaluationOverview:
    tender = await get_tender(db, tender_id)
    manifest = await get_latest_approved_manifest(db, tender_id)
    bidder = await get_bidder(db, tender_id, bidder_id)
    evidences = await get_extracted_evidence(db, tender_id, bidder_id)
    policy = load_policy()
    docs_by_name, fields_by_name = _group_evidence(evidences)
    threshold = float(policy["evaluation"]["ocr_confidence_threshold"])
    created_events: list[EvaluationEvent] = []

    for criterion in manifest.criteria:
        evidence_docs, missing_docs = _required_docs_present(criterion, docs_by_name)
        low_fields: list[str] = []
        for template in criterion.evidence_template:
            for field_name in template.required_fields:
                field, _ = _best_field(fields_by_name, field_name)
                if field is None or field.confidence < threshold:
                    low_fields.append(field_name)

        if missing_docs or low_fields:
            auto_verdict = "Needs Manual Review"
            match_logic = _low_evidence_reason(missing_docs, low_fields)
            extracted_values = {field_name: (_best_field(fields_by_name, field_name)[0].value if _best_field(fields_by_name, field_name)[0] else None) for field_name in set(low_fields)}
            flags: list[str] = []
            evidence_quality = "LOW"
        else:
            auto_verdict, match_logic, extracted_values, flags, evidence_quality = _evaluate_hard_rule(
                criterion,
                tender.bid_validity_end,
                fields_by_name,
                policy,
            )

        sequence, prior_event_id, prior_hash = await _next_sequence_and_prior(db, tender_id, bidder_id)
        payload = {
            "criterion_id": criterion.criterion_id,
            "criterion_name": criterion.factor,
            "sequence": sequence,
            "auto_verdict": auto_verdict,
            "final_verdict": auto_verdict,
            "match_logic": match_logic,
            "extracted_values": extracted_values,
            "flags": flags,
        }
        event = EvaluationEvent(
            _id=generate_id(),
            tender_id=tender_id,
            bidder_id=bidder_id,
            criterion_id=criterion.criterion_id,
            criterion_name=criterion.factor,
            stage=criterion.stage,
            criterion_type=criterion.type,
            classification=criterion.classification,
            event_type="AUTO_EVAL",
            sequence=sequence,
            evidence_docs=evidence_docs,
            extracted_values=extracted_values,
            evidence_quality=evidence_quality,
            match_logic=match_logic,
            auto_verdict=auto_verdict,
            final_verdict=auto_verdict,
            hard_disqualification_flags=flags,
            prior_event_id=prior_event_id,
            event_hash=_hash_event(payload, prior_hash),
        )
        await db.evaluation_events.insert_one(mongo_compatible(event))
        created_events.append(event)

    latest_events = _latest_by_criterion(created_events)
    hard_reasons = [
        reason
        for event in latest_events
        if event.final_verdict == "Not Eligible"
        for reason in event.hard_disqualification_flags
    ]
    hard_reasons.extend(_extra_bidder_level_reasons(bidder, fields_by_name))
    hard_disqualified = bool(hard_reasons)
    overall_status, reasons = _compute_overall_status(latest_events, hard_disqualified)
    if hard_reasons:
        reasons = list(dict.fromkeys(hard_reasons + reasons))

    await db.bidders.update_one(
        {"_id": bidder_id},
        {
            "$set": {
                "overall_status": overall_status,
                "hard_disqualified": hard_disqualified,
                "disqualification_reasons": reasons,
                "last_evaluated_at": _iso_now(),
                "updated_at": utcnow(),
            }
        },
    )
    return EvaluationOverview(
        tender_id=tender_id,
        bidder_id=bidder_id,
        overall_status=overall_status,
        hard_disqualified=hard_disqualified,
        disqualification_reasons=reasons,
        latest_events=latest_events,
    )


async def get_evaluation_overview(db: AsyncIOMotorDatabase, tender_id: str, bidder_id: str) -> EvaluationOverview:
    bidder = await get_bidder(db, tender_id, bidder_id)
    rows = await db.evaluation_events.find({"tender_id": tender_id, "bidder_id": bidder_id}).sort("sequence", 1).to_list(length=500)
    events = [EvaluationEvent(**row) for row in rows]
    latest = _latest_by_criterion(events)
    return EvaluationOverview(
        tender_id=tender_id,
        bidder_id=bidder_id,
        overall_status=bidder.overall_status,
        hard_disqualified=bidder.hard_disqualified,
        disqualification_reasons=bidder.disqualification_reasons,
        latest_events=latest,
    )


async def override_criterion(
    db: AsyncIOMotorDatabase,
    tender_id: str,
    bidder_id: str,
    criterion_id: str,
    payload: OverrideRequest,
    reviewer: User,
) -> EvaluationOverview:
    latest = await db.evaluation_events.find_one(
        {"tender_id": tender_id, "bidder_id": bidder_id, "criterion_id": criterion_id},
        sort=[("sequence", -1)],
    )
    if not latest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criterion evaluation not found.")

    prior = EvaluationEvent(**latest)
    sequence, prior_event_id, prior_hash = await _next_sequence_and_prior(db, tender_id, bidder_id)
    payload_for_hash = {
        "criterion_id": criterion_id,
        "sequence": sequence,
        "auto_verdict": prior.auto_verdict,
        "final_verdict": payload.final_verdict,
        "reason_code": payload.reason_code,
    }
    event = EvaluationEvent(
        _id=generate_id(),
        tender_id=tender_id,
        bidder_id=bidder_id,
        criterion_id=prior.criterion_id,
        criterion_name=prior.criterion_name,
        stage=prior.stage,
        criterion_type=prior.criterion_type,
        classification=prior.classification,
        event_type="OVERRIDE",
        sequence=sequence,
        evidence_docs=prior.evidence_docs,
        extracted_values=prior.extracted_values,
        evidence_quality=prior.evidence_quality,
        match_logic=prior.match_logic,
        auto_verdict=prior.auto_verdict,
        final_verdict=payload.final_verdict,
        hard_disqualification_flags=prior.hard_disqualification_flags,
        reason_code=payload.reason_code,
        reviewer_id=reviewer.username,
        reviewer_notes=payload.reviewer_notes,
        prior_event_id=prior_event_id,
        event_hash=_hash_event(payload_for_hash, prior_hash),
    )
    await db.evaluation_events.insert_one(mongo_compatible(event))

    rows = await db.evaluation_events.find({"tender_id": tender_id, "bidder_id": bidder_id}).sort("sequence", 1).to_list(length=500)
    events = _latest_by_criterion([EvaluationEvent(**row) for row in rows])
    evidences = await get_extracted_evidence(db, tender_id, bidder_id)
    _, fields_by_name = _group_evidence(evidences)
    bidder = await get_bidder(db, tender_id, bidder_id)
    hard_disqualified = any(
        event.final_verdict == "Not Eligible" and event.hard_disqualification_flags
        for event in events
    )
    extra_reasons = _extra_bidder_level_reasons(bidder, fields_by_name)
    hard_disqualified = hard_disqualified or bool(extra_reasons)
    overall_status, reasons = _compute_overall_status(events, hard_disqualified)
    if extra_reasons:
        reasons = list(dict.fromkeys(extra_reasons + reasons))
    await db.bidders.update_one(
        {"_id": bidder_id},
        {
            "$set": {
                "overall_status": overall_status,
                "hard_disqualified": hard_disqualified,
                "disqualification_reasons": reasons,
                "last_evaluated_at": _iso_now(),
                "updated_at": utcnow(),
            }
        },
    )
    return EvaluationOverview(
        tender_id=tender_id,
        bidder_id=bidder_id,
        overall_status=overall_status,
        hard_disqualified=hard_disqualified,
        disqualification_reasons=reasons,
        latest_events=events,
    )


def reason_codes() -> list[str]:
    return [
        "LOW_CONFIDENCE_CONFIRMED",
        "ADDITIONAL_EVIDENCE_ACCEPTED",
        "POLICY_EXCEPTION_APPROVED",
        "OCR_FALSE_NEGATIVE",
        "OFFICER_INTERPRETATION",
        "DOCUMENT_SCOPE_CLARIFIED",
    ]

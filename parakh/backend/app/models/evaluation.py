from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel

Verdict = Literal["Eligible", "Not Eligible", "Needs Manual Review"]
EvidenceQuality = Literal["HIGH", "LOW"]


class EvidenceDocRef(BaseModel):
    document_id: str
    doc_name: str
    filename: str
    relative_path: str


class EvaluationEvent(MongoModel):
    tender_id: str
    bidder_id: str
    criterion_id: str
    criterion_name: str
    stage: str
    criterion_type: str
    classification: str
    event_type: Literal["AUTO_EVAL", "OVERRIDE"] = "AUTO_EVAL"
    sequence: int
    evidence_docs: list[EvidenceDocRef] = Field(default_factory=list)
    extracted_values: dict[str, Any] = Field(default_factory=dict)
    evidence_quality: EvidenceQuality = "HIGH"
    match_logic: str
    auto_verdict: Verdict
    final_verdict: Verdict
    hard_disqualification_flags: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    reviewer_id: str | None = None
    reviewer_notes: str | None = None
    prior_event_id: str | None = None
    event_hash: str


class EvaluationOverview(BaseModel):
    tender_id: str
    bidder_id: str
    overall_status: str
    hard_disqualified: bool
    disqualification_reasons: list[str]
    latest_events: list[EvaluationEvent]


class OverrideRequest(BaseModel):
    final_verdict: Verdict
    reason_code: str
    reviewer_notes: str | None = None


class ClarificationRequest(MongoModel):
    tender_id: str
    bidder_id: str
    criterion_id: str
    request_text: str
    status: Literal["OPEN", "CLOSED"] = "OPEN"

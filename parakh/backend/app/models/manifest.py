from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel

CriterionClassification = Literal["hard", "graduated"]
CriterionType = Literal[
    "emd_rule",
    "certification_presence",
    "ballistic_level",
    "pattern_compliance",
    "quantity_capacity",
    "financial_threshold",
    "similar_work_history",
]


class EvidenceTemplate(BaseModel):
    doc_name: str
    doc_description: str | None = None
    required_fields: list[str] = Field(default_factory=list)
    required: bool = True


class Criterion(BaseModel):
    criterion_id: str
    stage: str
    factor: str
    description: str
    type: CriterionType
    classification: CriterionClassification
    mandatory: bool = True
    normalized_threshold: dict[str, Any] = Field(default_factory=dict)
    evidence_template: list[EvidenceTemplate] = Field(default_factory=list)
    guidance_notes: str | None = None


class CriteriaManifestVersion(MongoModel):
    tender_id: str
    version: int
    status: Literal["DRAFT", "APPROVED", "SUPERSEDED"] = "DRAFT"
    generated_from: str = "evaluation_criteria.csv"
    source_documents: list[str] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    approved_at: str | None = None
    approved_by: str | None = None

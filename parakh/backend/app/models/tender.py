from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel


class TenderDocument(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    relative_path: str
    uploaded_at: str


class TenderCreate(BaseModel):
    title: str
    procuring_entity: str
    bid_reference: str
    description: str | None = None
    bid_validity_end: date | None = None


class ManifestUpdateRequest(BaseModel):
    criteria: list[dict] = Field(default_factory=list)


class Tender(MongoModel):
    title: str
    procuring_entity: str
    bid_reference: str
    description: str | None = None
    bid_validity_end: date | None = None
    status: Literal["DRAFT", "ACTIVE", "CLOSED"] = "DRAFT"
    documents: list[TenderDocument] = Field(default_factory=list)
    latest_manifest_id: str | None = None
    created_by: str | None = None

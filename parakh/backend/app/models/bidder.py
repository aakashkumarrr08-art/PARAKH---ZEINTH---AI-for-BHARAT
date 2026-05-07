from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel


class BidderDocument(BaseModel):
    document_id: str
    filename: str
    doc_name: str
    relative_path: str
    content_type: str | None = None
    uploaded_at: str


class BidderCreate(BaseModel):
    name: str
    bidder_type: Literal["OEM", "AUTHORIZED_BIDDER"] = "AUTHORIZED_BIDDER"
    oem_name: str | None = None


class ChecklistStatusItem(BaseModel):
    doc_name: str
    doc_description: str
    doc_purpose: str
    uploaded: bool = False
    document_id: str | None = None
    filename: str | None = None


class Bidder(MongoModel):
    tender_id: str
    name: str
    bidder_type: Literal["OEM", "AUTHORIZED_BIDDER"] = "AUTHORIZED_BIDDER"
    oem_name: str | None = None
    documents: list[BidderDocument] = Field(default_factory=list)
    checklist_status: list[ChecklistStatusItem] = Field(default_factory=list)
    overall_status: Literal["PENDING", "OK", "DISQUALIFIED", "UNDER_REVIEW"] = "PENDING"
    hard_disqualified: bool = False
    disqualification_reasons: list[str] = Field(default_factory=list)
    last_evaluated_at: str | None = None

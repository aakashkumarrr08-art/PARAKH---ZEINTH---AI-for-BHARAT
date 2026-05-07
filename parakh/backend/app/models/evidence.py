from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel


class ExtractedField(BaseModel):
    name: str
    value: Any = None
    confidence: float = 0.0
    source_text: str | None = None
    page_numbers: list[int] = Field(default_factory=list)


class ExtractedEvidence(MongoModel):
    tender_id: str
    bidder_id: str
    document_id: str
    doc_name: str
    filename: str
    relative_path: str
    extraction_method: Literal["digital_text", "ocr", "html", "fallback"]
    text_preview: str
    fields: list[ExtractedField] = Field(default_factory=list)
    overall_confidence: float = 0.0

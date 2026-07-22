from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REPROCESS = "reprocess"


class DocumentRecord(BaseModel):
    id: str
    batch_id: str
    source_filename: str
    document_type: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    raw_text: str = Field(default="", exclude=True, repr=False)
    locations: list[str] = Field(default_factory=list)
    extracted_text: str = ""
    redacted_text: str = ""
    classification: str = ""
    summary: str = ""
    key_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: str = ""
    error: str | None = None
    redaction_counts: dict[str, int] = Field(default_factory=dict)


class BatchRecord(BaseModel):
    id: str
    document_ids: list[str] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.UPLOADED

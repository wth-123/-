from __future__ import annotations

from .models import DocumentRecord, DocumentStatus
from .provider import ModelProvider
from .redaction import Redactor


def organize_document(
    record: DocumentRecord,
    provider: ModelProvider,
    redactor: Redactor | None = None,
) -> DocumentRecord:
    """脱敏后调用模型提供者，并将整理结果写回内存记录。"""
    redaction = (redactor or Redactor()).redact(record.raw_text)
    result = provider.organize(redaction.text, record.document_type)

    record.redacted_text = redaction.text
    record.redaction_counts = redaction.counts
    record.classification = str(result["classification"])
    record.summary = str(result["summary"])
    record.key_fields = dict(result["key_fields"])
    record.confidence = float(result["confidence"])
    record.evidence = list(result["evidence"])
    record.status = DocumentStatus.PROCESSED
    return record

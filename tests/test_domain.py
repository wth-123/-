from __future__ import annotations

import json
import logging

from app.domain.config import Settings
from app.domain.logging import log_document_event
from app.domain.models import BatchRecord, DocumentRecord, DocumentStatus, ReviewStatus
from app.domain.organization import organize_document
from app.domain.provider import MockModelProvider
from app.domain.redaction import Redactor


def test_document_record_hides_raw_text_from_serialization() -> None:
    record = DocumentRecord(
        id="doc-1",
        batch_id="batch-1",
        source_filename="contract.txt",
        document_type="contract",
        raw_text="internal 13800138000",
    )

    assert record.status is DocumentStatus.UPLOADED
    assert record.review_status is ReviewStatus.PENDING
    assert "raw_text" not in record.model_dump()
    assert "13800138000" not in repr(record)
    assert record.raw_text == "internal 13800138000"


def test_batch_record_groups_document_ids() -> None:
    batch = BatchRecord(id="batch-1", document_ids=["doc-1", "doc-2"])

    assert batch.document_ids == ["doc-1", "doc-2"]


def test_redactor_removes_phone_email_and_identity_card() -> None:
    source = "张三电话13800138000，邮箱zhang.san@example.com，身份证11010519491231002X。"

    result = Redactor().redact(source)

    assert "13800138000" not in result.text
    assert "zhang.san@example.com" not in result.text
    assert "11010519491231002X" not in result.text
    assert result.text.count("[REDACTED_PHONE]") == 1
    assert result.text.count("[REDACTED_EMAIL]") == 1
    assert result.text.count("[REDACTED_ID_CARD]") == 1
    assert result.counts == {"phone": 1, "email": 1, "id_card": 1}


def test_mock_provider_receives_only_redacted_content_and_is_deterministic() -> None:
    raw_text = "联系人 13800138000"
    redacted = Redactor().redact(raw_text).text
    provider = MockModelProvider()

    first = provider.organize(redacted, "contract")
    second = provider.organize(redacted, "contract")

    assert first == second
    assert first["classification"] == "contract"
    assert "13800138000" not in json.dumps(first, ensure_ascii=False)


def test_mock_provider_handles_empty_text() -> None:
    result = MockModelProvider().organize("", "")

    assert result["classification"] == "未分类"
    assert result["summary"] == "无可整理文本"
    assert result["key_fields"] == {}
    assert result["confidence"] == 0.0
    assert result["evidence"] == []


def test_organize_document_sends_only_redacted_text_to_provider() -> None:
    class CapturingProvider:
        def __init__(self) -> None:
            self.received_text = ""

        def organize(self, redacted_text: str, document_type: str) -> dict:
            self.received_text = redacted_text
            return {
                "classification": document_type,
                "summary": "organized",
                "key_fields": {"title": "example"},
                "confidence": 0.8,
                "evidence": [],
            }

    record = DocumentRecord(
        id="doc-2",
        batch_id="batch-1",
        source_filename="notice.txt",
        document_type="notice",
        raw_text="请联系 13800138000",
    )
    provider = CapturingProvider()

    organized = organize_document(record, provider, Redactor())

    assert "13800138000" not in provider.received_text
    assert "[REDACTED_PHONE]" in provider.received_text
    assert organized.redacted_text == provider.received_text
    assert organized.redaction_counts == {"phone": 1, "email": 0, "id_card": 0}
    assert organized.classification == "notice"
    assert organized.status is DocumentStatus.PROCESSED


def test_settings_returns_defaults_without_config_file(tmp_path) -> None:
    settings = Settings.load(tmp_path / "missing.json")

    assert settings.categories
    assert settings.key_fields
    assert {"phone", "email", "id_card"}.issubset(settings.redaction_types)
    assert settings.model_provider == "mock"


def test_settings_loads_editable_json_config(tmp_path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "categories": ["invoice"],
                "key_fields": {"invoice": ["invoice_number"]},
                "redaction_types": ["email"],
                "model_provider": "custom",
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.load(config_path)

    assert settings.categories == ["invoice"]
    assert settings.key_fields == {"invoice": ["invoice_number"]}
    assert settings.redaction_types == {"email"}
    assert settings.model_provider == "custom"


def test_safe_log_contains_only_allowlisted_metadata(caplog) -> None:
    raw_text = "13800138000 zhang@example.com"
    redacted_text = "[REDACTED_PHONE] [REDACTED_EMAIL]"

    with caplog.at_level(logging.INFO):
        log_document_event(
            filename="contract.txt",
            status=DocumentStatus.PROCESSED,
            error=ValueError("model request failed"),
            redaction_counts={"phone": 1, "email": 1, "id_card": 0},
            raw_text=raw_text,
            redacted_text=redacted_text,
            model_request={"content": redacted_text},
        )

    message = caplog.records[-1].getMessage()
    assert "contract.txt" in message
    assert "processed" in message
    assert "ValueError" in message
    assert '"phone": 1' in message
    assert raw_text not in message
    assert redacted_text not in message
    assert "content" not in message

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from .models import DocumentStatus


LOGGER = logging.getLogger("app.domain")


def log_document_event(
    *,
    filename: str,
    status: DocumentStatus | str,
    error: BaseException | None = None,
    redaction_counts: Mapping[str, int] | None = None,
    raw_text: str | None = None,
    redacted_text: str | None = None,
    model_request: Mapping[str, Any] | None = None,
) -> None:
    """记录允许的元数据；文本参数仅用于兼容调用，绝不写入日志。"""
    del raw_text, redacted_text, model_request
    event = {
        "filename": filename,
        "status": status.value if isinstance(status, DocumentStatus) else status,
        "error_category": type(error).__name__ if error else None,
        "redaction_counts": dict(redaction_counts or {}),
    }
    LOGGER.info("document_event=%s", json.dumps(event, ensure_ascii=False, sort_keys=True))

from __future__ import annotations

from typing import Any, Protocol


class ModelProvider(Protocol):
    def organize(self, redacted_text: str, document_type: str) -> dict[str, Any]:
        """将已脱敏的文本整理为固定结构。"""


class MockModelProvider:
    """不调用外部模型的确定性实现，仅接收已脱敏的内容。"""

    def organize(self, redacted_text: str, document_type: str) -> dict[str, Any]:
        if not redacted_text.strip():
            return {
                "classification": "未分类",
                "summary": "无可整理文本",
                "key_fields": {},
                "confidence": 0.0,
                "evidence": [],
            }

        classification = document_type.strip() or "未分类"
        return {
            "classification": classification,
            "summary": f"已整理 {classification} 文档",
            "key_fields": {},
            "confidence": 1.0,
            "evidence": [],
        }

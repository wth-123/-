from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["合同", "发票", "报告", "其他"])
    key_fields: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "合同": ["合同编号", "签署方", "签署日期"],
            "发票": ["发票号码", "金额", "开票日期"],
            "报告": ["标题", "日期"],
        }
    )
    redaction_types: set[str] = Field(
        default_factory=lambda: {"phone", "email", "id_card"}
    )
    model_provider: str = "mock"

    @classmethod
    def load(cls, config_path: str | Path) -> "Settings":
        path = Path(config_path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as config_file:
            return cls.model_validate(json.load(config_file))

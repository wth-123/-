from __future__ import annotations

from pathlib import Path

from .domain.models import BatchRecord, DocumentRecord


class MemoryStore:
    def __init__(self) -> None:
        self.upload_root = Path("data/uploads")
        self.reset()

    def reset(self) -> None:
        self.batches: dict[str, BatchRecord] = {}
        self.documents: dict[str, DocumentRecord] = {}


store = MemoryStore()

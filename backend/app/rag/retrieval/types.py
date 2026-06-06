from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalResult:
    chunk_id: str
    text: str
    score: float
    source: str
    payload: dict[str, Any]
    point_id: str | None = None


# ============================================================
# TAFA V7 PRO — Feature Store
# ============================================================
"""In-memory feature store for training samples."""

from __future__ import annotations

from typing import Any, Optional


class FeatureStore:
    """Simple list-backed feature store."""

    def __init__(self) -> None:
        self.features: list[dict[str, Any]] = []

    def add(self, data: dict[str, Any]) -> None:
        self.features.append(data)

    def dataset(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        if limit is not None:
            return self.features[-limit:]
        return list(self.features)

    def clear(self) -> None:
        self.features = []

    def __len__(self) -> int:
        return len(self.features)

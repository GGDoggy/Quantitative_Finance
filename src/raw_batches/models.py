from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawBatch:
    product_id: str
    timestamp: str
    init_path: Path
    updates_path: Path
    trade_path: Path
    is_preprocessed: bool = False

    @property
    def batch_id(self) -> str:
        return f"{self.product_id}|{self.timestamp}"

    @property
    def file_stem(self) -> str:
        return f"{self.product_id}-{self.timestamp}"

    @property
    def display_name(self) -> str:
        from .naming import parse_timestamp

        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        suffix = " | preprocessed" if self.is_preprocessed else ""
        return f"{self.product_id} | {formatted}{suffix}"

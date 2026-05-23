from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .models import RawBatch


_RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_TRADE_RE = re.compile(
    r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)


@dataclass(frozen=True)
class RawFilenameMetadata:
    product_id: str
    timestamp: str
    kind: str


def parse_raw_filename(filename: str) -> RawFilenameMetadata | None:
    for kind, pattern in (
        ("init", _RAW_LEVEL2_INIT_RE),
        ("updates", _RAW_LEVEL2_UPDATES_RE),
        ("trade", _RAW_TRADE_RE),
    ):
        match = pattern.match(filename)
        if match is None:
            continue
        return RawFilenameMetadata(
            product_id=match.group("product_id"),
            timestamp=match.group("timestamp"),
            kind=kind,
        )
    return None


def discover_raw_batches(raw_dir: Path | str) -> list[RawBatch]:
    grouped: dict[tuple[str, str], dict[str, Path]] = {}
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        return []

    for path in sorted(raw_path.glob("*.csv")):
        metadata = parse_raw_filename(path.name)
        if metadata is None:
            continue
        grouped.setdefault((metadata.product_id, metadata.timestamp), {})[
            metadata.kind
        ] = path

    batches: list[RawBatch] = []
    for (product_id, timestamp), parts in sorted(grouped.items()):
        if {"init", "updates", "trade"} - set(parts):
            continue
        batches.append(
            RawBatch(
                product_id=product_id,
                timestamp=timestamp,
                init_path=parts["init"],
                updates_path=parts["updates"],
                trade_path=parts["trade"],
            )
        )
    return batches

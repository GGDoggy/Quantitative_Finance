from __future__ import annotations

import calendar
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


_RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_TRADE_RE = re.compile(
    r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d.%H%M%S")


def file_time_to_unix(file_time: str) -> int:
    return calendar.timegm(parse_timestamp(file_time).timetuple())


@dataclass(frozen=True)
class RawFilenameMetadata:
    product_id: str
    timestamp: str
    kind: str


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
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        suffix = " | preprocessed" if self.is_preprocessed else ""
        return f"{self.product_id} | {formatted}{suffix}"


@dataclass(frozen=True)
class LoadedRawBatch:
    init: list[list[float]]
    updates: list[list[float]]
    trades: list[list[float]]
    start_time: float


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


def _read_csv_rows(path: Path) -> list[list[float]]:
    with path.open(newline="") as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        return [list(row) for row in reader]


def load_raw_batch(batch: RawBatch) -> LoadedRawBatch:
    return LoadedRawBatch(
        init=_read_csv_rows(batch.init_path),
        updates=_read_csv_rows(batch.updates_path),
        trades=_read_csv_rows(batch.trade_path),
        start_time=file_time_to_unix(batch.timestamp),
    )

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .models import RawBatch
from .naming import file_time_to_unix


@dataclass(frozen=True)
class LoadedRawBatch:
    init: list[list[float]]
    updates: list[list[float]]
    trades: list[list[float]]
    start_time: float


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

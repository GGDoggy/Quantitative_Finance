from __future__ import annotations

import calendar
import csv
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from gui.data_catalog import RawBatch


@dataclass(frozen=True)
class PreprocessContext:
    batch: "RawBatch"
    time_step: float
    init_rows: list[list[float]]
    updates_rows: list[list[float]]
    trade_rows: list[list[float]]


def read_csv_rows(path: Path) -> list[list[float]]:
    with path.open(newline="") as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        return [list(row) for row in reader]


def build_context(batch: RawBatch, time_step: float) -> PreprocessContext:
    return PreprocessContext(
        batch=batch,
        time_step=time_step,
        init_rows=read_csv_rows(batch.init_path),
        updates_rows=read_csv_rows(batch.updates_path),
        trade_rows=read_csv_rows(batch.trade_path),
    )


def file_time_to_unix(file_time: str) -> int:
    seconds = time.strptime(file_time, "%Y%m%d.%H%M%S")
    return calendar.timegm(seconds)


def build_trade_arrays(
    trade_rows: list[list[float]],
    timestamp: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not trade_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        return empty_time, empty_float, empty_float, empty_float

    start_time = datetime.strptime(timestamp, "%Y%m%d.%H%M%S")
    midnight = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    trade_time = np.array(
        [midnight + timedelta(seconds=row[0]) for row in trade_rows],
        dtype="datetime64[ns]",
    )
    trade_price = np.array([row[1] for row in trade_rows], dtype=float)
    trade_volume = np.array([row[2] for row in trade_rows], dtype=float)
    trade_side = np.array([row[3] for row in trade_rows], dtype=float)
    return trade_time, trade_price, trade_volume, trade_side

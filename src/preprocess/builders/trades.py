from __future__ import annotations

from datetime import timedelta

import numpy as np

from src.preprocess.models import PreprocessContext
from src.raw_batches import parse_timestamp


def build_trade_arrays(
    trade_rows: list[list[float]],
    timestamp: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not trade_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        return empty_time, empty_float, empty_float, empty_float

    start_time = parse_timestamp(timestamp)
    midnight = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    trade_time = np.array(
        [midnight + timedelta(seconds=row[0]) for row in trade_rows],
        dtype="datetime64[ns]",
    )
    trade_price = np.array([row[1] for row in trade_rows], dtype=float)
    trade_volume = np.array([row[2] for row in trade_rows], dtype=float)
    trade_side = np.array([row[3] for row in trade_rows], dtype=float)
    return trade_time, trade_price, trade_volume, trade_side


def build_trade_payload(context: PreprocessContext) -> dict[str, object]:
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(
        context.trade_rows,
        context.batch.timestamp,
    )
    return {
        "trade_time": trade_time,
        "trade_price": trade_price,
        "trade_volume": trade_volume,
        "trade_side": trade_side,
    }

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .pipeline import PreprocessContext


def _empty_trade_payload() -> dict[str, object]:
    empty_time = np.array([], dtype="datetime64[ns]")
    empty_float = np.array([], dtype=float)
    return {
        "trade_time": empty_time,
        "trade_price": empty_float,
        "trade_volume": empty_float,
        "trade_side": empty_float,
    }


def _sorted_trade_rows(trade_rows: list[list[float]]) -> np.ndarray:
    if not trade_rows:
        return np.empty((0, 4), dtype=float)

    rows = np.asarray(trade_rows, dtype=float)
    if rows.ndim != 2 or rows.shape[1] != 4:
        raise ValueError("Trade rows must be a 2D array with columns: time, price, volume, side.")

    order = np.argsort(rows[:, 0], kind="stable")
    return rows[order]


def build_trade_payload(context: PreprocessContext) -> dict[str, object]:
    trade_rows = _sorted_trade_rows(context.trades_rows)
    if trade_rows.size == 0:
        return _empty_trade_payload()

    day_origin = np.datetime64(int(context.start_time), "s").astype("datetime64[D]")
    trade_time = day_origin + (trade_rows[:, 0] * 1_000_000_000).astype("timedelta64[ns]")
    return {
        "trade_time": np.asarray(trade_time, dtype="datetime64[ns]"),
        "trade_price": np.asarray(trade_rows[:, 1], dtype=float),
        "trade_volume": np.asarray(trade_rows[:, 2], dtype=float),
        "trade_side": np.asarray(trade_rows[:, 3], dtype=float),
    }

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import numpy as np

from .time_utils import (
    compute_trimmed_window,
    event_seconds_to_datetime64,
    iter_bucket_starts,
    sort_and_normalize_event_seconds,
    sorted_update_times,
)

if TYPE_CHECKING:
    from .pipeline import PreprocessContext


def _trade_window_key(base_name: str, trade_window_seconds: int) -> str:
    return f"{base_name}__w{trade_window_seconds}"


def _empty_trade_payload(trade_window_seconds: int) -> dict[str, object]:
    empty_time = np.array([], dtype="datetime64[ns]")
    empty_float = np.array([], dtype=float)
    return {
        _trade_window_key("trade_time", trade_window_seconds): empty_time,
        _trade_window_key("trade_price", trade_window_seconds): empty_float,
        _trade_window_key("trade_volume", trade_window_seconds): empty_float,
        _trade_window_key("trade_side", trade_window_seconds): empty_float,
        "trade_window_seconds_available": np.asarray([trade_window_seconds], dtype=int),
        "trade_window_seconds_latest": int(trade_window_seconds),
    }


def _sorted_trade_rows(trade_rows: list[list[float]]) -> np.ndarray:
    if not trade_rows:
        return np.empty((0, 4), dtype=float)

    rows = np.asarray(trade_rows, dtype=float)
    if rows.ndim != 2 or rows.shape[1] != 4:
        raise ValueError("Trade rows must be a 2D array with columns: time, price, volume, side.")

    normalized_seconds, order = sort_and_normalize_event_seconds(rows[:, 0])
    ordered_rows = rows[order].copy()
    ordered_rows[:, 0] = normalized_seconds
    return ordered_rows


def _aggregate_trade_rows(
    rows: np.ndarray,
    bucket_starts: Iterable[float],
    trade_window_seconds: int,
) -> np.ndarray:
    starts = [float(start) for start in bucket_starts]
    if rows.size == 0 or not starts:
        return np.empty((0, 4), dtype=float)

    bucket_map = {bucket_start: index for index, bucket_start in enumerate(starts)}
    first_bucket_start = starts[0]
    last_bucket_end = starts[-1] + trade_window_seconds
    aggregates: dict[tuple[float, float, float], float] = {}

    for trade_time, price, volume, side in rows:
        trade_time = float(trade_time)
        if trade_time < first_bucket_start or trade_time >= last_bucket_end:
            continue
        bucket_offset = int((trade_time - first_bucket_start) // trade_window_seconds)
        bucket_start = first_bucket_start + (bucket_offset * trade_window_seconds)
        if bucket_start not in bucket_map:
            continue
        if trade_time >= bucket_start + trade_window_seconds:
            continue
        key = (bucket_start, float(price), float(side))
        aggregates[key] = aggregates.get(key, 0.0) + float(volume)

    if not aggregates:
        return np.empty((0, 4), dtype=float)

    ordered_keys = sorted(aggregates, key=lambda item: (item[0], item[1], item[2]))
    return np.asarray(
        [
            [bucket_start, price, aggregates[(bucket_start, price, side)], side]
            for bucket_start, price, side in ordered_keys
        ],
        dtype=float,
    )


def build_trade_payload(context: PreprocessContext) -> dict[str, object]:
    trade_window_seconds = int(context.trade_window_seconds)
    trade_rows = _sorted_trade_rows(context.trades_rows)
    if trade_rows.size == 0:
        return _empty_trade_payload(trade_window_seconds)

    update_times = sorted_update_times(context.updates_rows)
    trimmed_window = compute_trimmed_window(trade_rows[:, 0], update_times)
    if trimmed_window is None:
        return _empty_trade_payload(trade_window_seconds)

    bucket_starts = list(
        iter_bucket_starts(
            trimmed_window[0],
            trimmed_window[1],
            trade_window_seconds,
        )
    )
    aggregated_rows = _aggregate_trade_rows(
        trade_rows,
        bucket_starts,
        trade_window_seconds,
    )
    if aggregated_rows.size == 0:
        return _empty_trade_payload(trade_window_seconds)

    day_origin = np.datetime64(int(context.start_time), "s").astype("datetime64[D]")
    trade_time = event_seconds_to_datetime64(aggregated_rows[:, 0], day_origin)
    return {
        _trade_window_key("trade_time", trade_window_seconds): np.asarray(
            trade_time,
            dtype="datetime64[ns]",
        ),
        _trade_window_key("trade_price", trade_window_seconds): np.asarray(
            aggregated_rows[:, 1],
            dtype=float,
        ),
        _trade_window_key("trade_volume", trade_window_seconds): np.asarray(
            aggregated_rows[:, 2],
            dtype=float,
        ),
        _trade_window_key("trade_side", trade_window_seconds): np.asarray(
            aggregated_rows[:, 3],
            dtype=float,
        ),
        "trade_window_seconds_available": np.asarray([trade_window_seconds], dtype=int),
        "trade_window_seconds_latest": int(trade_window_seconds),
    }

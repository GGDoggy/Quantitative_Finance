from __future__ import annotations

from bisect import bisect_left, insort
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


def _signed_book_volume(volume: float, side: float) -> float:
    normalized_side = int(side)
    if normalized_side == 1:
        return float(volume)
    if normalized_side == -1:
        return -float(volume)
    raise ValueError(f"Unsupported orderbook side: {side}")


def update_orderbook(
    orderbook: np.ndarray,
    price_index: dict[float, int],
    bid_indices: list[int],
    ask_indices: list[int],
    price: float | np.floating,
    volume: float,
    side: float,
) -> None:
    index = price_index[float(price)]
    previous_value = orderbook[index]
    new_value = _signed_book_volume(volume, side)

    if previous_value > 0:
        remove_at = bisect_left(bid_indices, index)
        if remove_at < len(bid_indices) and bid_indices[remove_at] == index:
            bid_indices.pop(remove_at)
    elif previous_value < 0:
        remove_at = bisect_left(ask_indices, index)
        if remove_at < len(ask_indices) and ask_indices[remove_at] == index:
            ask_indices.pop(remove_at)

    orderbook[index] = new_value
    if new_value > 0:
        insort(bid_indices, index)
    elif new_value < 0:
        insort(ask_indices, index)


def get_bid_ask(
    price_levels: np.ndarray,
    bid_indices: list[int],
    ask_indices: list[int],
) -> tuple[float, float]:
    bid = price_levels[bid_indices[-1]] if bid_indices else np.nan
    ask = price_levels[ask_indices[0]] if ask_indices else np.nan
    return float(bid), float(ask)


def _snapshot_book_side(
    price_levels: np.ndarray,
    orderbook: np.ndarray,
    indices: list[int],
    depth: int,
    *,
    is_bid: bool,
) -> tuple[np.ndarray, np.ndarray]:
    prices = np.full(depth, np.nan, dtype=float)
    sizes = np.zeros(depth, dtype=float)
    if not indices:
        return prices, sizes

    selected = indices[-depth:][::-1] if is_bid else indices[:depth]
    for dest_index, source_index in enumerate(selected):
        prices[dest_index] = float(price_levels[source_index])
        raw_size = float(orderbook[source_index])
        sizes[dest_index] = raw_size if is_bid else -raw_size
    return prices, sizes


def _orderbook_window_key(base_name: str, trade_window_seconds: int) -> str:
    return f"{base_name}__w{trade_window_seconds}"


def _empty_orderbook_payload(
    trade_window_seconds: int,
    depth: int,
) -> dict[str, object]:
    empty_time = np.array([], dtype="datetime64[ns]")
    empty_float = np.array([], dtype=float)
    empty_price_snapshot = np.full((0, depth), np.nan, dtype=float)
    empty_size_snapshot = np.zeros((0, depth), dtype=float)
    return {
        _orderbook_window_key("time_axis", trade_window_seconds): empty_time,
        _orderbook_window_key("bid_price", trade_window_seconds): empty_price_snapshot,
        _orderbook_window_key("bid_size", trade_window_seconds): empty_size_snapshot,
        _orderbook_window_key("ask_price", trade_window_seconds): empty_price_snapshot.copy(),
        _orderbook_window_key("ask_size", trade_window_seconds): empty_size_snapshot.copy(),
        _orderbook_window_key("bid", trade_window_seconds): empty_float,
        _orderbook_window_key("ask", trade_window_seconds): empty_float,
        _orderbook_window_key("mid", trade_window_seconds): empty_float,
        "orderbook_window_seconds_available": np.asarray([trade_window_seconds], dtype=int),
        "orderbook_window_seconds_latest": int(trade_window_seconds),
    }


def build_orderbook_history(
    init_rows: list[list[float]],
    update_rows: list[list[float]],
    trade_rows: list[list[float]],
    start_time: int,
    depth: int,
    trade_window_seconds: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    if not update_rows or not trade_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        empty_price_snapshot = np.full((0, depth), np.nan, dtype=float)
        empty_size_snapshot = np.zeros((0, depth), dtype=float)
        return (
            empty_time,
            empty_price_snapshot,
            empty_size_snapshot,
            empty_price_snapshot.copy(),
            empty_size_snapshot.copy(),
            empty_float,
            empty_float,
            empty_float,
        )

    update_rows_array = np.asarray(update_rows, dtype=float)
    if update_rows_array.ndim != 2 or update_rows_array.shape[1] != 4:
        raise ValueError("Update rows must be a 2D array with columns: time, price, volume, side.")
    trade_rows_array = np.asarray(trade_rows, dtype=float)
    if trade_rows_array.ndim != 2 or trade_rows_array.shape[1] != 4:
        raise ValueError("Trade rows must be a 2D array with columns: time, price, volume, side.")

    normalized_trade_times, _ = sort_and_normalize_event_seconds(trade_rows_array[:, 0])
    normalized_update_times = sorted_update_times(update_rows)
    trimmed_window = compute_trimmed_window(normalized_trade_times, normalized_update_times)
    if trimmed_window is None:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        empty_price_snapshot = np.full((0, depth), np.nan, dtype=float)
        empty_size_snapshot = np.zeros((0, depth), dtype=float)
        return (
            empty_time,
            empty_price_snapshot,
            empty_size_snapshot,
            empty_price_snapshot.copy(),
            empty_size_snapshot.copy(),
            empty_float,
            empty_float,
            empty_float,
        )

    bucket_starts = np.asarray(
        list(iter_bucket_starts(trimmed_window[0], trimmed_window[1], trade_window_seconds)),
        dtype=float,
    )
    if bucket_starts.size == 0:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        empty_price_snapshot = np.full((0, depth), np.nan, dtype=float)
        empty_size_snapshot = np.zeros((0, depth), dtype=float)
        return (
            empty_time,
            empty_price_snapshot,
            empty_size_snapshot,
            empty_price_snapshot.copy(),
            empty_size_snapshot.copy(),
            empty_float,
            empty_float,
            empty_float,
        )

    price_levels = {row[0] for row in init_rows}
    price_levels.update(row[1] for row in update_rows)
    sorted_prices = np.array(sorted(price_levels), dtype=float)
    if sorted_prices.size == 0:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        empty_price_snapshot = np.full((0, depth), np.nan, dtype=float)
        empty_size_snapshot = np.zeros((0, depth), dtype=float)
        return (
            empty_time,
            empty_price_snapshot,
            empty_size_snapshot,
            empty_price_snapshot.copy(),
            empty_size_snapshot.copy(),
            empty_float,
            empty_float,
            empty_float,
        )

    price_index = {
        float(price): index
        for index, price in enumerate(sorted_prices.tolist())
    }
    orderbook = np.zeros(len(sorted_prices), dtype=float)
    bid_indices: list[int] = []
    ask_indices: list[int] = []
    for level in init_rows:
        update_orderbook(
            orderbook,
            price_index,
            bid_indices,
            ask_indices,
            level[0],
            level[1],
            level[2],
        )

    day_origin = np.datetime64(start_time, "s").astype("datetime64[D]")
    normalized_seconds, order = sort_and_normalize_event_seconds(update_rows_array[:, 0])
    ordered_updates = update_rows_array[order]
    ordered_update_times = normalized_seconds
    snapshot_times = event_seconds_to_datetime64(bucket_starts, day_origin)
    snapshot_count = len(bucket_starts)
    bid_prices = np.full((snapshot_count, depth), np.nan, dtype=float)
    bid_sizes = np.zeros((snapshot_count, depth), dtype=float)
    ask_prices = np.full((snapshot_count, depth), np.nan, dtype=float)
    ask_sizes = np.zeros((snapshot_count, depth), dtype=float)
    bids = np.full(snapshot_count, np.nan, dtype=float)
    asks = np.full(snapshot_count, np.nan, dtype=float)

    update_index = 0
    for row_index, bucket_start in enumerate(bucket_starts):
        while (
            update_index < len(ordered_updates)
            and ordered_update_times[update_index] < bucket_start
        ):
            update = ordered_updates[update_index]
            update_orderbook(
                orderbook,
                price_index,
                bid_indices,
                ask_indices,
                update[1],
                update[2],
                update[3],
            )
            update_index += 1

        bid, ask = get_bid_ask(sorted_prices, bid_indices, ask_indices)
        bids[row_index] = bid
        asks[row_index] = ask
        bid_prices[row_index], bid_sizes[row_index] = _snapshot_book_side(
            sorted_prices,
            orderbook,
            bid_indices,
            depth,
            is_bid=True,
        )
        ask_prices[row_index], ask_sizes[row_index] = _snapshot_book_side(
            sorted_prices,
            orderbook,
            ask_indices,
            depth,
            is_bid=False,
        )

    mid_array = 0.5 * (bids + asks)

    return (
        snapshot_times,
        bid_prices,
        bid_sizes,
        ask_prices,
        ask_sizes,
        bids,
        asks,
        mid_array,
    )


def build_orderbook_payload(context: PreprocessContext) -> dict[str, object]:
    trade_window_seconds = int(context.trade_window_seconds)
    time_axis, bid_price, bid_size, ask_price, ask_size, bid, ask, mid = build_orderbook_history(
        context.init_rows,
        context.updates_rows,
        context.trades_rows,
        int(context.start_time),
        context.depth,
        trade_window_seconds,
    )
    if time_axis.shape == (0,):
        return _empty_orderbook_payload(trade_window_seconds, context.depth)
    return {
        _orderbook_window_key("time_axis", trade_window_seconds): time_axis,
        _orderbook_window_key("bid_price", trade_window_seconds): bid_price,
        _orderbook_window_key("bid_size", trade_window_seconds): bid_size,
        _orderbook_window_key("ask_price", trade_window_seconds): ask_price,
        _orderbook_window_key("ask_size", trade_window_seconds): ask_size,
        _orderbook_window_key("bid", trade_window_seconds): bid,
        _orderbook_window_key("ask", trade_window_seconds): ask,
        _orderbook_window_key("mid", trade_window_seconds): mid,
        "orderbook_window_seconds_available": np.asarray([trade_window_seconds], dtype=int),
        "orderbook_window_seconds_latest": int(trade_window_seconds),
    }

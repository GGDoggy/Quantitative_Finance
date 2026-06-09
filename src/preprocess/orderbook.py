from __future__ import annotations

from bisect import bisect_left, insort
from typing import TYPE_CHECKING

import numpy as np

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


def build_orderbook_history(
    init_rows: list[list[float]],
    update_rows: list[list[float]],
    start_time: int,
    depth: int,
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
    price_levels = {row[0] for row in init_rows}
    price_levels.update(row[1] for row in update_rows)
    sorted_prices = np.array(sorted(price_levels), dtype=float)

    if sorted_prices.size == 0 or not update_rows:
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
    sorted_updates = sorted(update_rows)
    update_count = len(sorted_updates)
    snapshot_times = np.empty(update_count, dtype="datetime64[ns]")
    bid_prices = np.full((update_count, depth), np.nan, dtype=float)
    bid_sizes = np.zeros((update_count, depth), dtype=float)
    ask_prices = np.full((update_count, depth), np.nan, dtype=float)
    ask_sizes = np.zeros((update_count, depth), dtype=float)
    bids = np.full(update_count, np.nan, dtype=float)
    asks = np.full(update_count, np.nan, dtype=float)

    for row_index, update in enumerate(sorted_updates):
        update_orderbook(
            orderbook,
            price_index,
            bid_indices,
            ask_indices,
            update[1],
            update[2],
            update[3],
        )
        snapshot_times[row_index] = day_origin + np.timedelta64(
            int(update[0] * 1_000_000_000),
            "ns",
        )
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
    time_axis, bid_price, bid_size, ask_price, ask_size, bid, ask, mid = build_orderbook_history(
        context.init_rows,
        context.updates_rows,
        int(context.start_time),
        context.depth,
    )
    return {
        "time_axis": time_axis,
        "bid_price": bid_price,
        "bid_size": bid_size,
        "ask_price": ask_price,
        "ask_size": ask_size,
        "bid": bid,
        "ask": ask,
        "mid": mid,
    }

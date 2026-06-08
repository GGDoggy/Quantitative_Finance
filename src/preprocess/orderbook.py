from __future__ import annotations

from bisect import bisect_left, insort
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .pipeline import PreprocessContext


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
    new_value = volume * side * -1

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


def build_orderbook_history(
    init_rows: list[list[float]],
    update_rows: list[list[float]],
    start_time: int,
    depth: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    price_levels = {row[0] for row in init_rows}
    price_levels.update(row[1] for row in update_rows)
    sorted_prices = np.array(sorted(price_levels), dtype=float)

    if sorted_prices.size == 0 or not update_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        return (
            np.array([], dtype=float),
            empty_time,
            np.zeros((0, 0), dtype=float),
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
    snapshot_times: list[np.datetime64] = []
    bids: list[float] = []
    asks: list[float] = []
    row_indices: list[list[int]] = []
    row_values: list[list[float]] = []
    active_index_set: set[int] = set()

    for update in sorted_updates:
        update_orderbook(
            orderbook,
            price_index,
            bid_indices,
            ask_indices,
            update[1],
            update[2],
            update[3],
        )
        snapshot_times.append(day_origin + np.timedelta64(int(update[0] * 1_000_000_000), "ns"))
        bid, ask = get_bid_ask(sorted_prices, bid_indices, ask_indices)
        bids.append(bid)
        asks.append(ask)
        visible = bid_indices[-depth:] + ask_indices[:depth]
        active_index_set.update(visible)
        row_indices.append(visible)
        row_values.append([float(orderbook[index]) for index in visible])

    active_indices = np.array(sorted(active_index_set), dtype=int)
    if active_indices.size == 0:
        active_price_axis = np.array([], dtype=float)
        data = np.zeros((len(sorted_updates), 0), dtype=float)
    else:
        active_price_axis = sorted_prices[active_indices]
        remap = {
            source_index: dest_index
            for dest_index, source_index in enumerate(active_indices.tolist())
        }
        data = np.zeros((len(sorted_updates), len(active_indices)), dtype=float)

        for row_index, (indices, values) in enumerate(zip(row_indices, row_values, strict=True)):
            for source_index, value in zip(indices, values, strict=True):
                data[row_index, remap[source_index]] = value

    bid_array = np.asarray(bids, dtype=float)
    ask_array = np.asarray(asks, dtype=float)
    mid_array = 0.5 * (bid_array + ask_array)

    return (
        active_price_axis,
        np.asarray(snapshot_times, dtype="datetime64[ns]"),
        data,
        bid_array,
        ask_array,
        mid_array,
    )


def build_orderbook_payload(context: PreprocessContext) -> dict[str, object]:
    price_axis, time_axis, data, bid, ask, mid = build_orderbook_history(
        context.init_rows,
        context.updates_rows,
        int(context.start_time),
        context.depth,
    )
    return {
        "price_axis": price_axis,
        "time_axis": time_axis,
        "data": data,
        "bid": bid,
        "ask": ask,
        "mid": mid,
    }

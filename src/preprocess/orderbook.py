from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .pipeline import PreprocessContext


def update_orderbook(
    orderbook: np.ndarray,
    price_levels: np.ndarray,
    price: float,
    volume: float,
    side: float,
) -> None:
    index = np.searchsorted(price_levels, price)
    orderbook[index] = volume * side * -1


def get_bid_ask(orderbook: np.ndarray, price_levels: np.ndarray) -> tuple[float, float]:
    bid_indices = np.flatnonzero(orderbook > 0)
    ask_indices = np.flatnonzero(orderbook < 0)
    bid = price_levels[bid_indices[-1]] if bid_indices.size else np.nan
    ask = price_levels[ask_indices[0]] if ask_indices.size else np.nan
    return float(bid), float(ask)


def _visible_depth_indices(orderbook: np.ndarray, depth: int) -> np.ndarray:
    bid_indices = np.flatnonzero(orderbook > 0)
    ask_indices = np.flatnonzero(orderbook < 0)

    selected: list[int] = []
    if bid_indices.size:
        selected.extend(bid_indices[-depth:].tolist())
    if ask_indices.size:
        selected.extend(ask_indices[:depth].tolist())

    if not selected:
        return np.array([], dtype=int)
    return np.array(sorted(set(selected)), dtype=int)


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

    orderbook = np.zeros(len(sorted_prices), dtype=float)
    for level in init_rows:
        update_orderbook(orderbook, sorted_prices, level[0], level[1], level[2])

    day_origin = np.datetime64(start_time, "s").astype("datetime64[D]")
    snapshots: list[np.ndarray] = []
    snapshot_times: list[np.datetime64] = []
    bids: list[float] = []
    asks: list[float] = []
    visible_indices: list[np.ndarray] = []

    for update in sorted(update_rows):
        update_orderbook(orderbook, sorted_prices, update[1], update[2], update[3])
        snapshot_times.append(day_origin + np.timedelta64(int(update[0] * 1_000_000_000), "ns"))
        snapshots.append(orderbook.copy())
        bid, ask = get_bid_ask(orderbook, sorted_prices)
        bids.append(bid)
        asks.append(ask)
        visible_indices.append(_visible_depth_indices(orderbook, depth))

    active_indices = np.unique(np.concatenate(visible_indices))
    if active_indices.size == 0:
        active_price_axis = np.array([], dtype=float)
        data = np.zeros((len(snapshots), 0), dtype=float)
    else:
        active_price_axis = sorted_prices[active_indices]
        remap = {source_index: dest_index for dest_index, source_index in enumerate(active_indices.tolist())}
        data = np.zeros((len(snapshots), len(active_indices)), dtype=float)
        for row_index, (snapshot, indices) in enumerate(zip(snapshots, visible_indices, strict=True)):
            for source_index in indices.tolist():
                data[row_index, remap[source_index]] = snapshot[source_index]

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

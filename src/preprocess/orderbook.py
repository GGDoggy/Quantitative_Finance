from __future__ import annotations

import calendar
from datetime import datetime, timedelta
import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .pipeline import PreprocessContext


def update_orderbook(orderbook: np.ndarray, price_levels: np.ndarray, price: float, volume: float, side: float) -> None:
    index = np.searchsorted(price_levels, price)
    orderbook[index] = volume * side * -1


def get_bid_ask(orderbook: np.ndarray, price_levels: np.ndarray) -> tuple[float, float]:
    bid = np.nan
    ask = np.nan

    for index, volume in enumerate(orderbook):
        if volume > 0:
            break
        if volume != 0:
            bid = price_levels[index]

    last_index = len(orderbook) - 1
    for offset in range(last_index + 1):
        volume = orderbook[last_index - offset]
        if volume < 0:
            break
        if volume != 0:
            ask = price_levels[last_index - offset]

    return bid, ask


def build_orderbook_history(
    init_rows: list[list[float]],
    update_rows: list[list[float]],
    start_time: int,
    time_step: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    price_levels = {row[0] for row in init_rows}
    price_levels.update(row[1] for row in update_rows)
    sorted_prices = np.array(sorted(price_levels))

    orderbook = np.zeros(len(sorted_prices))
    for level in init_rows:
        update_orderbook(orderbook, sorted_prices, level[0], level[1], level[2])

    orderbook_list: list[np.ndarray] = []
    bids: list[float] = []
    asks: list[float] = []

    start_dt = datetime.utcfromtimestamp(start_time)
    time_origin = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    step = timedelta(seconds=time_step)
    current_time = time_origin
    updates = sorted(update_rows)
    index = 0
    sample_count = 0
    started = False
    end_time = current_time

    while index < len(updates):
        next_update_time = time_origin + timedelta(seconds=updates[index][0])
        if current_time < next_update_time:
            if started:
                orderbook_list.append(orderbook.copy())
                bid, ask = get_bid_ask(orderbook, sorted_prices)
                bids.append(bid)
                asks.append(ask)
                end_time = current_time
                sample_count += 1
            current_time += step
            continue

        update_orderbook(orderbook, sorted_prices, updates[index][1], updates[index][2], updates[index][3])
        started = True
        index += 1

    orderbook_list.append(orderbook.copy())
    bid, ask = get_bid_ask(orderbook, sorted_prices)
    bids.append(bid)
    asks.append(ask)
    end_time = current_time
    sample_count += 1

    aligned_start_time = end_time - step * (sample_count - 1)
    time_axis = aligned_start_time + np.arange(sample_count) * step
    bid_array = np.array(bids)
    ask_array = np.array(asks)
    mid_array = 0.5 * (bid_array + ask_array)

    return (
        sorted_prices,
        np.array(time_axis, dtype="datetime64[ns]"),
        np.array(orderbook_list),
        bid_array,
        ask_array,
        mid_array,
    )


def build_orderbook_payload(context: PreprocessContext) -> dict[str, object]:
    parsed = time.strptime(context.batch.timestamp, "%Y%m%d.%H%M%S")
    price_axis, time_axis, data, bid, ask, mid = build_orderbook_history(
        context.init_rows,
        context.updates_rows,
        calendar.timegm(parsed),
        context.time_step,
    )
    return {
        "price_axis": price_axis,
        "time_axis": time_axis,
        "data": data,
        "bid": bid,
        "ask": ask,
        "mid": mid,
    }

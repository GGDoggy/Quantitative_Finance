from __future__ import annotations

import calendar
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import numpy as np

from gui.data_catalog import PreprocessedDataset, RawBatch, discover_preprocessed_datasets


DEFAULT_TIME_STEP = 0.01
AVAILABLE_VIEWS = ("orderbook", "trades_scatter", "trade_volume_timeline")


def read_csv_rows(path: Path) -> list[list[float]]:
    with path.open(newline="") as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        return [list(row) for row in reader]


def file_time_to_unix(file_time: str) -> int:
    seconds = time.strptime(file_time, "%Y%m%d.%H%M%S")
    return calendar.timegm(seconds)


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


def build_trade_arrays(trade_rows: list[list[float]], timestamp: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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


def preprocess_batch(
    batch: RawBatch,
    output_dir: Path,
    time_step: float = DEFAULT_TIME_STEP,
) -> PreprocessedDataset:
    init_rows = read_csv_rows(batch.init_path)
    updates_rows = read_csv_rows(batch.updates_path)
    trade_rows = read_csv_rows(batch.trade_path)

    price_axis, time_axis, data, bid, ask, mid = build_orderbook_history(
        init_rows,
        updates_rows,
        file_time_to_unix(batch.timestamp),
        time_step,
    )
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(trade_rows, batch.timestamp)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{batch.product_id}-{batch.timestamp}-{time_step}-orderbook_for_plot.npz"
    np.savez_compressed(
        output_path,
        price_axis=price_axis,
        time_axis=time_axis,
        data=data,
        bid=bid,
        ask=ask,
        mid=mid,
        trade_time=trade_time,
        trade_price=trade_price,
        trade_volume=trade_volume,
        trade_side=trade_side,
        available_views=np.array(AVAILABLE_VIEWS),
    )

    for dataset in discover_preprocessed_datasets(output_dir):
        if dataset.path == output_path:
            return dataset

    raise FileNotFoundError(f"Failed to discover freshly written dataset: {output_path}")


def preprocess_batches(
    batches: list[RawBatch],
    output_dir: Path,
    time_step: float = DEFAULT_TIME_STEP,
    progress_callback: Callable[[str], None] | None = None,
) -> list[PreprocessedDataset]:
    results: list[PreprocessedDataset] = []
    total = len(batches)

    for index, batch in enumerate(batches, start=1):
        if progress_callback is not None:
            progress_callback(f"[{index}/{total}] preprocessing {batch.display_name}")
        results.append(preprocess_batch(batch, output_dir=output_dir, time_step=time_step))

    if progress_callback is not None and batches:
        progress_callback(f"Finished preprocessing {len(batches)} batch(es).")

    return results

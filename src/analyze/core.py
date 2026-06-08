from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

from .models import AnalyzeResult, LoadedAnalyzeData


def _sorted_rows(rows: Iterable[list[float]]) -> list[list[float]]:
    return sorted(rows, key=lambda row: float(row[0]))


def _apply_level_update(levels: dict[float, float], price: float, volume: float) -> None:
    if volume <= 0:
        levels.pop(price, None)
        return
    levels[price] = volume


def _initialize_book(init_rows: list[list[float]]) -> tuple[dict[float, float], dict[float, float]]:
    bid_levels: dict[float, float] = {}
    ask_levels: dict[float, float] = {}
    for price_raw, volume_raw, side_raw in init_rows:
        price = float(price_raw)
        volume = float(volume_raw)
        side = int(side_raw)
        if side == -1:
            _apply_level_update(bid_levels, price, volume)
        else:
            _apply_level_update(ask_levels, price, volume)
    return bid_levels, ask_levels


def _best_bid(levels: dict[float, float]) -> tuple[float, float]:
    if not levels:
        return np.nan, 0.0
    price = max(levels)
    return float(price), float(levels[price])


def _best_ask(levels: dict[float, float]) -> tuple[float, float]:
    if not levels:
        return np.nan, 0.0
    price = min(levels)
    return float(price), float(levels[price])


def _spread(best_bid_price: float, best_ask_price: float) -> float:
    if not (np.isfinite(best_bid_price) and np.isfinite(best_ask_price)):
        return np.nan
    return float(best_ask_price - best_bid_price)


def _side_name(trade_side: float) -> str:
    return "bid" if int(trade_side) == 1 else "ask"


def _price_sort_key(side: str, price: float) -> float:
    return -price if side == "bid" else price


def _is_better_than_last(side: str, price: float, last_price: float) -> bool:
    if side == "bid":
        return price > last_price and not np.isclose(price, last_price)
    return price < last_price and not np.isclose(price, last_price)


def _fill_rate(
    *,
    penetrated: bool,
    traded_volume: float,
    starting_volume: float,
) -> float:
    if penetrated:
        return 1.0
    if starting_volume <= 0:
        return np.nan
    return float(traded_volume / starting_volume)


def analyze_loaded_data(data: LoadedAnalyzeData) -> AnalyzeResult:
    bid_levels, ask_levels = _initialize_book(data.init)
    updates = _sorted_rows(data.updates)
    trades = _sorted_rows(data.trades)

    if len(updates) < 2 or not trades:
        empty_float = np.array([], dtype=float)
        return AnalyzeResult(
            price=empty_float,
            vol=empty_float.copy(),
            time=empty_float.copy(),
            side=np.array([], dtype="<U3"),
            penetrated=np.array([], dtype=bool),
            spread=empty_float.copy(),
            opp_vol=empty_float.copy(),
            fill_rate=empty_float.copy(),
        )

    trade_index = 0
    trade_count = len(trades)
    rows: list[tuple[float, float, float, str, bool, float, float, float]] = []

    for current_update, next_update in zip(updates, updates[1:]):
        current_price = float(current_update[1])
        current_volume = float(current_update[2])
        current_side = int(current_update[3])
        if current_side == -1:
            _apply_level_update(bid_levels, current_price, current_volume)
        else:
            _apply_level_update(ask_levels, current_price, current_volume)

        interval_start = float(current_update[0])
        interval_end = float(next_update[0])

        while trade_index < trade_count and float(trades[trade_index][0]) < interval_start:
            trade_index += 1

        grouped_volume: dict[tuple[str, float], float] = defaultdict(float)
        last_price_by_side: dict[str, float] = {}

        scan_index = trade_index
        while scan_index < trade_count and float(trades[scan_index][0]) < interval_end:
            trade = trades[scan_index]
            side = _side_name(trade[3])
            price = float(trade[1])
            grouped_volume[(side, price)] += float(trade[2])
            last_price_by_side[side] = price
            scan_index += 1

        trade_index = scan_index
        if not grouped_volume:
            continue

        best_bid_price, best_bid_size = _best_bid(bid_levels)
        best_ask_price, best_ask_size = _best_ask(ask_levels)
        spread = _spread(best_bid_price, best_ask_price)

        for side in ("bid", "ask"):
            last_price = last_price_by_side.get(side)
            if last_price is None:
                continue

            side_prices = sorted(
                (price for trade_side, price in grouped_volume if trade_side == side),
                key=lambda price: _price_sort_key(side, price),
            )
            for price in side_prices:
                traded_volume = float(grouped_volume[(side, price)])
                penetrated = _is_better_than_last(side, price, last_price)
                levels = bid_levels if side == "bid" else ask_levels
                starting_volume = float(levels.get(price, 0.0))
                rows.append(
                    (
                        price,
                        traded_volume,
                        interval_start,
                        side,
                        penetrated,
                        spread,
                        best_ask_size if side == "bid" else best_bid_size,
                        _fill_rate(
                            penetrated=penetrated,
                            traded_volume=traded_volume,
                            starting_volume=starting_volume,
                        ),
                    )
                )

    if not rows:
        empty_float = np.array([], dtype=float)
        return AnalyzeResult(
            price=empty_float,
            vol=empty_float.copy(),
            time=empty_float.copy(),
            side=np.array([], dtype="<U3"),
            penetrated=np.array([], dtype=bool),
            spread=empty_float.copy(),
            opp_vol=empty_float.copy(),
            fill_rate=empty_float.copy(),
        )

    return AnalyzeResult(
        price=np.asarray([row[0] for row in rows], dtype=float),
        vol=np.asarray([row[1] for row in rows], dtype=float),
        time=np.asarray([row[2] for row in rows], dtype=float),
        side=np.asarray([row[3] for row in rows], dtype="<U3"),
        penetrated=np.asarray([row[4] for row in rows], dtype=bool),
        spread=np.asarray([row[5] for row in rows], dtype=float),
        opp_vol=np.asarray([row[6] for row in rows], dtype=float),
        fill_rate=np.asarray([row[7] for row in rows], dtype=float),
    )

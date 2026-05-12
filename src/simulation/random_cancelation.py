import calendar
import csv
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


@dataclass
class VirtualOrder:
    submit_time: float
    price: float
    near_size: float
    opp_size: float
    ahead: float
    behind: float
    vorder_ratio: float
    remaining_size: float
    result: int = -1
    survival_time: float = -1.0


@dataclass
class TradeEvidence:
    price: float
    volume: float
    event_time: float


def read_csv(path):
    with open(path) as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        data = list(reader)
    return data


def file_time_to_unix(file_time):
    sec = time.strptime(file_time, "%Y%m%d.%H%M%S")
    return calendar.timegm(sec)


def unix_to_daily_seconds(unix_time):
    dt = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    return (
        dt.hour * 3600
        + dt.minute * 60
        + dt.second
        + dt.microsecond / 1_000_000
    )


def same_price(lhs, rhs):
    if np.isnan(lhs) or np.isnan(rhs):
        return False
    return np.isclose(lhs, rhs)


def update_orderbook(orderbook, price_levels, price, volume, side):
    ind = np.searchsorted(price_levels, price)
    orderbook[ind] = volume * side * -1


def get_best_levels(orderbook, price_levels):
    bid_indices = np.where(orderbook < 0)[0]
    ask_indices = np.where(orderbook > 0)[0]

    if len(bid_indices) == 0:
        best_bid_price = np.nan
        best_bid_size = 0.0
    else:
        bid_index = bid_indices[-1]
        best_bid_price = price_levels[bid_index]
        best_bid_size = -orderbook[bid_index]

    if len(ask_indices) == 0:
        best_ask_price = np.nan
        best_ask_size = 0.0
    else:
        ask_index = ask_indices[0]
        best_ask_price = price_levels[ask_index]
        best_ask_size = orderbook[ask_index]

    return best_bid_price, best_bid_size, best_ask_price, best_ask_size


def build_event_stream(updates, trades):
    events = []
    for update in updates:
        events.append((update[0], 1, "update", update[1], update[2], int(update[3])))
    for trade in trades:
        events.append((trade[0], 0, "trade", trade[1], trade[2], int(trade[3])))
    events.sort(key=lambda item: (item[0], item[1]))
    return events


def side_to_trade_key(trade_side):
    return "bid" if trade_side == 1 else "ask"


def is_worse_best_price_change(book_side, previous_price, current_price):
    if np.isnan(previous_price) or np.isnan(current_price):
        return False
    if book_side == "bid":
        return current_price < previous_price and not same_price(current_price, previous_price)
    return current_price > previous_price and not same_price(current_price, previous_price)


def trade_reaches_price(book_side, trade_price, level_price):
    if np.isnan(level_price):
        return False
    if book_side == "bid":
        return trade_price <= level_price or same_price(trade_price, level_price)
    return trade_price >= level_price or same_price(trade_price, level_price)


def trade_hits_level(book_side, trade_price, level_price):
    return same_price(trade_price, level_price)


def create_virtual_order(best_size, opp_size, submit_time, submit_price, base_tick):
    if np.isnan(submit_price) or best_size <= 0:
        return None
    return VirtualOrder(
        submit_time=submit_time,
        price=float(submit_price),
        near_size=float(best_size),
        opp_size=float(opp_size),
        ahead=float(best_size),
        behind=0.0,
        vorder_ratio=float(base_tick / best_size),
        remaining_size=float(base_tick),
    )


def finalize_order(order, end_time, result):
    if order.result != -1:
        return
    order.result = result
    order.survival_time = float(end_time - order.submit_time)
    order.ahead = max(order.ahead, 0.0)
    order.behind = max(order.behind, 0.0)


def get_active_orders_at_price(active_orders, price):
    return [order for order in active_orders if order.result == -1 and same_price(order.price, price)]


def apply_size_delta(active_orders, delta):
    if not active_orders or delta == 0:
        return

    if delta > 0:
        for order in active_orders:
            if order.result == -1:
                order.behind += delta
        return

    reduction = -delta
    for order in active_orders:
        if order.result != -1:
            continue
        total_queue = order.ahead + order.behind
        if total_queue <= 0:
            continue
        ahead_reduction = reduction * order.ahead / total_queue
        behind_reduction = reduction * order.behind / total_queue
        order.ahead = max(order.ahead - ahead_reduction, 0.0)
        order.behind = max(order.behind - behind_reduction, 0.0)


def apply_trade_volume(active_orders, traded_size, event_time):
    if traded_size <= 0:
        return

    for order in active_orders:
        if order.result != -1:
            continue

        if order.ahead > 0:
            ahead_consumed = min(order.ahead, traded_size)
            order.ahead -= ahead_consumed
            traded_size -= ahead_consumed

        if traded_size <= 0:
            continue

        fill_size = min(order.remaining_size, traded_size)
        order.remaining_size -= fill_size
        traded_size -= fill_size

        if order.remaining_size <= 0:
            finalize_order(order, event_time, 1)


def append_trade_evidence(pending_trade_evidence, trade_side, price, volume, event_time):
    trade_key = side_to_trade_key(trade_side)
    pending_trade_evidence[trade_key].append(
        TradeEvidence(price=float(price), volume=float(volume), event_time=float(event_time))
    )


def split_trade_evidence(records, book_side, level_price):
    traded_at_level = 0.0
    traded_at_level_time = None
    traded_through_level = 0.0
    traded_through_level_time = None

    for record in records:
        if trade_hits_level(book_side, record.price, level_price):
            traded_at_level += record.volume
            traded_at_level_time = record.event_time
        if trade_reaches_price(book_side, record.price, level_price):
            traded_through_level += record.volume
            traded_through_level_time = record.event_time

    return (
        traded_at_level,
        traded_at_level_time,
        traded_through_level,
        traded_through_level_time,
    )


def reconcile_same_best_price(active_orders, size_delta, traded_at_level, event_time):
    if not active_orders:
        return

    if traded_at_level > 0:
        apply_trade_volume(active_orders, traded_at_level, event_time)

    residual = size_delta + traded_at_level
    if not np.isclose(residual, 0.0):
        apply_size_delta(active_orders, residual)


def reconcile_price_change(active_orders, has_sweep_evidence, event_time):
    for order in active_orders:
        if order.result != -1:
            continue
        finalize_order(order, event_time, 1 if has_sweep_evidence else 0)


def reconcile_one_side(
    book_side,
    active_orders,
    previous_best_price,
    previous_best_size,
    current_best_price,
    current_best_size,
    pending_trade_records,
    update_event_time,
):
    if np.isnan(previous_best_price):
        return False

    orders_at_previous_best = get_active_orders_at_price(active_orders, previous_best_price)
    best_price_unchanged = same_price(previous_best_price, current_best_price)
    best_size_unchanged = np.isclose(previous_best_size, current_best_size)
    if best_price_unchanged and best_size_unchanged:
        return False

    (
        traded_at_level,
        traded_at_level_time,
        traded_through_level,
        traded_through_level_time,
    ) = split_trade_evidence(pending_trade_records, book_side, previous_best_price)

    if best_price_unchanged:
        reconcile_same_best_price(
            orders_at_previous_best,
            current_best_size - previous_best_size,
            traded_at_level,
            traded_at_level_time if traded_at_level_time is not None else update_event_time,
        )
        return True

    if is_worse_best_price_change(book_side, previous_best_price, current_best_price):
        has_sweep_evidence = traded_through_level > 0
        reconcile_price_change(
            orders_at_previous_best,
            has_sweep_evidence,
            traded_through_level_time if traded_through_level_time is not None else update_event_time,
        )
        return True

    reconcile_price_change(orders_at_previous_best, False, update_event_time)
    return True


def finalize_unresolved(orders):
    price = np.array([order.price for order in orders], dtype=float)
    near_size = np.array([order.near_size for order in orders], dtype=float)
    opp_size = np.array([order.opp_size for order in orders], dtype=float)
    survival_time = np.array([order.survival_time for order in orders], dtype=float)
    ahead = np.array([max(order.ahead, 0.0) for order in orders], dtype=float)
    behind = np.array([max(order.behind, 0.0) for order in orders], dtype=float)
    vorder_ratio = np.array([order.vorder_ratio for order in orders], dtype=float)
    result = np.array([order.result for order in orders], dtype=int)
    return price, near_size, opp_size, survival_time, ahead, behind, vorder_ratio, result


def empty_outputs():
    empty_sim = np.array([], dtype=float)
    empty_result = np.array([], dtype=int)
    return (
        empty_sim,
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_result,
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_result.copy(),
    )


def simulate_virtual_best_orders(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
):
    price_levels = {level[0] for level in init}
    price_levels.update(update[1] for update in updates)
    price_levels = np.array(sorted(price_levels), dtype=float)

    orderbook = np.zeros(len(price_levels), dtype=float)
    for level in init:
        update_orderbook(orderbook, price_levels, level[0], level[1], level[2])

    orderbook_start_time = min(update[0] for update in updates) if updates else unix_to_daily_seconds(start_time)
    orderbook_end_time = max(update[0] for update in updates) if updates else orderbook_start_time

    if not trades:
        return empty_outputs()

    trade_start_time = min(trade[0] for trade in trades)
    trade_end_time = max(trade[0] for trade in trades)
    simulation_start = max(orderbook_start_time, trade_start_time) + 1.0
    simulation_end = min(orderbook_end_time, trade_end_time) - 1.0

    if simulation_end < simulation_start:
        return empty_outputs()

    events = build_event_stream(updates, trades)
    event_index = 0
    next_submit_time = simulation_start
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders = []
    ask_orders = []

    while event_index < len(events) or next_submit_time <= simulation_end:
        next_event_time = events[event_index][0] if event_index < len(events) else float("inf")

        if next_event_time <= next_submit_time and event_index < len(events):
            (
                event_time,
                _priority,
                event_type,
                event_price,
                event_volume,
                event_side,
            ) = events[event_index]
            event_index += 1

            best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels(orderbook, price_levels)

            if event_type == "trade":
                append_trade_evidence(
                    pending_trade_evidence,
                    event_side,
                    event_price,
                    event_volume,
                    event_time,
                )
                continue

            previous_bid_price = best_bid_price
            previous_bid_size = best_bid_size
            previous_ask_price = best_ask_price
            previous_ask_size = best_ask_size

            update_orderbook(orderbook, price_levels, event_price, event_volume, event_side)

            current_bid_price, current_bid_size, current_ask_price, current_ask_size = get_best_levels(
                orderbook, price_levels
            )

            bid_consumed = reconcile_one_side(
                "bid",
                bid_orders,
                previous_bid_price,
                previous_bid_size,
                current_bid_price,
                current_bid_size,
                pending_trade_evidence["bid"],
                event_time,
            )
            ask_consumed = reconcile_one_side(
                "ask",
                ask_orders,
                previous_ask_price,
                previous_ask_size,
                current_ask_price,
                current_ask_size,
                pending_trade_evidence["ask"],
                event_time,
            )

            if bid_consumed:
                pending_trade_evidence["bid"].clear()
            if ask_consumed:
                pending_trade_evidence["ask"].clear()
            continue

        if next_submit_time > simulation_end:
            break

        best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels(orderbook, price_levels)

        bid_order = create_virtual_order(
            best_bid_size,
            best_ask_size,
            next_submit_time,
            best_bid_price,
            base_tick,
        )
        if bid_order is not None:
            bid_orders.append(bid_order)

        ask_order = create_virtual_order(
            best_ask_size,
            best_bid_size,
            next_submit_time,
            best_ask_price,
            base_tick,
        )
        if ask_order is not None:
            ask_orders.append(ask_order)

        next_submit_time += time_step

    for order in bid_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)
    for order in ask_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)

    return (
        *finalize_unresolved(bid_orders),
        *finalize_unresolved(ask_orders),
    )

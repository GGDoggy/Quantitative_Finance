import calendar
import csv
import os
import time
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

ALGORITHM_NAME = "time_averaged_random_cancellation"
DEFAULT_RESOLVED_TIME = 1.0
DEBUG_BEST_STATE = os.environ.get("DEBUG_BEST_STATE", "").lower() in {"1", "true", "yes", "on"}


@dataclass
class VirtualOrder:
    submit_time: float
    price: float
    near_size: float
    opp_size: float
    spread: float
    ahead: float
    behind: float
    vorder_ratio: float
    remaining_size: float
    result: int = -1
    survival_time: float = -1.0
    fill_time: float = np.nan


@dataclass
class TradeEvidence:
    price: float
    volume: float
    event_time: float


@dataclass
class TradeEvidenceSummary:
    volume: float
    last_event_time: float | None


@dataclass
class TradeEvidenceIndex:
    event_times: list[float]
    at_level_cumulative_volume: list[float]
    at_level_last_times: list[float | None]
    through_level_cumulative_volume: list[float]
    through_level_last_times: list[float | None]

    def _position_at_or_before(self, event_time):
        return bisect_right(self.event_times, event_time)

    def at_level_at_or_before(self, event_time):
        position = self._position_at_or_before(event_time)
        return self._summary_at_position(
            self.at_level_cumulative_volume,
            self.at_level_last_times,
            position,
        )

    def at_level_after(self, event_time):
        position = self._position_at_or_before(event_time)
        return self._summary_after_position(
            self.at_level_cumulative_volume,
            self.at_level_last_times,
            position,
        )

    def through_level_after(self, event_time):
        position = self._position_at_or_before(event_time)
        return self._summary_after_position(
            self.through_level_cumulative_volume,
            self.through_level_last_times,
            position,
        )

    @staticmethod
    def _summary_at_position(cumulative_volume, last_times, position):
        if position <= 0:
            return TradeEvidenceSummary(0.0, None)
        return TradeEvidenceSummary(cumulative_volume[position - 1], last_times[position - 1])

    @staticmethod
    def _summary_after_position(cumulative_volume, last_times, position):
        if not cumulative_volume:
            return TradeEvidenceSummary(0.0, None)

        before_volume = cumulative_volume[position - 1] if position > 0 else 0.0
        volume = cumulative_volume[-1] - before_volume
        last_time = last_times[-1] if volume > 0 else None
        return TradeEvidenceSummary(volume, last_time)


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


def get_price_index(price_levels, price):
    return int(np.searchsorted(price_levels, price))


def update_orderbook(orderbook, price_levels, price, volume, side):
    price_index = get_price_index(price_levels, price)
    orderbook[price_index] = volume * side * -1
    return price_index, orderbook[price_index]


def initialize_best_indices(orderbook):
    best_bid_index = None
    best_ask_index = None

    for index in range(len(orderbook) - 1, -1, -1):
        if orderbook[index] < 0:
            best_bid_index = index
            break

    for index in range(len(orderbook)):
        if orderbook[index] > 0:
            best_ask_index = index
            break

    return best_bid_index, best_ask_index


def has_valid_bid_at_index(orderbook, price_index):
    return price_index is not None and orderbook[price_index] < 0


def has_valid_ask_at_index(orderbook, price_index):
    return price_index is not None and orderbook[price_index] > 0


def refresh_best_indices(orderbook, best_bid_index, best_ask_index):
    if has_valid_bid_at_index(orderbook, best_bid_index) and has_valid_ask_at_index(orderbook, best_ask_index):
        return best_bid_index, best_ask_index
    return initialize_best_indices(orderbook)


def advance_best_bid_index(orderbook, updated_index, current_best_index):
    if current_best_index is None:
        if orderbook[updated_index] < 0:
            return updated_index
        return None

    if updated_index > current_best_index and orderbook[updated_index] < 0:
        return updated_index

    if updated_index != current_best_index:
        return current_best_index

    if orderbook[current_best_index] < 0:
        return current_best_index

    for index in range(current_best_index - 1, -1, -1):
        if orderbook[index] < 0:
            return index
    return None


def advance_best_ask_index(orderbook, updated_index, current_best_index):
    if current_best_index is None:
        if orderbook[updated_index] > 0:
            return updated_index
        return None

    if updated_index < current_best_index and orderbook[updated_index] > 0:
        return updated_index

    if updated_index != current_best_index:
        return current_best_index

    if orderbook[current_best_index] > 0:
        return current_best_index

    for index in range(current_best_index + 1, len(orderbook)):
        if orderbook[index] > 0:
            return index
    return None


def get_best_levels_from_indices(orderbook, price_levels, best_bid_index, best_ask_index):
    if best_bid_index is None:
        best_bid_price = np.nan
        best_bid_size = 0.0
    else:
        best_bid_price = price_levels[best_bid_index]
        best_bid_size = -orderbook[best_bid_index]

    if best_ask_index is None:
        best_ask_price = np.nan
        best_ask_size = 0.0
    else:
        best_ask_price = price_levels[best_ask_index]
        best_ask_size = orderbook[best_ask_index]

    return best_bid_price, best_bid_size, best_ask_price, best_ask_size


def debug_best_state(
    stage,
    orderbook,
    price_levels,
    best_bid_index,
    best_ask_index,
    best_bid_price,
    best_bid_size,
    best_ask_price,
    best_ask_size,
    event_time=None,
    event_type=None,
    event_price=None,
    event_volume=None,
    event_side=None,
    updated_index=None,
):
    if not DEBUG_BEST_STATE:
        return

    bid_raw = None if best_bid_index is None else float(orderbook[best_bid_index])
    ask_raw = None if best_ask_index is None else float(orderbook[best_ask_index])
    bid_invalid = best_bid_index is not None and bid_raw >= 0.0
    ask_invalid = best_ask_index is not None and ask_raw <= 0.0

    if not (bid_invalid or ask_invalid):
        return

    print(
        "[DEBUG_BEST_STATE]",
        f"stage={stage}",
        f"time={event_time}",
        f"event_type={event_type}",
        f"event_side={event_side}",
        f"event_price={event_price}",
        f"event_volume={event_volume}",
        f"updated_index={updated_index}",
        f"bid_index={best_bid_index}",
        f"bid_price={best_bid_price}",
        f"bid_size={best_bid_size}",
        f"bid_raw={bid_raw}",
        f"ask_index={best_ask_index}",
        f"ask_price={best_ask_price}",
        f"ask_size={best_ask_size}",
        f"ask_raw={ask_raw}",
    )


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


def compute_bid_ask_spread(best_bid_price, best_ask_price):
    if not (np.isfinite(best_bid_price) and np.isfinite(best_ask_price)):
        return np.nan
    return float(best_ask_price - best_bid_price)


def create_virtual_order(best_size, opp_size, spread, submit_time, submit_price, base_tick):
    if np.isnan(submit_price) or best_size <= 0:
        return None
    return VirtualOrder(
        submit_time=submit_time,
        price=float(submit_price),
        near_size=float(best_size),
        opp_size=float(opp_size),
        spread=float(spread),
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
    order.fill_time = float(end_time) if result == 1 else np.nan
    order.ahead = max(order.ahead, 0.0)
    order.behind = max(order.behind, 0.0)


def get_orders_bucket(orders_by_price, price_index):
    if price_index is None:
        return []
    return orders_by_price.setdefault(price_index, [])


def get_active_orders_at_index(orders_by_price, price_index):
    if price_index is None:
        return []
    return [order for order in orders_by_price.get(price_index, []) if order.result == -1]


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


def build_trade_evidence_index(records, book_side, level_price):
    event_times = []
    at_level_cumulative_volume = []
    at_level_last_times = []
    through_level_cumulative_volume = []
    through_level_last_times = []

    at_level_total = 0.0
    at_level_last_time = None
    through_level_total = 0.0
    through_level_last_time = None

    for record in records:
        event_times.append(record.event_time)

        if trade_hits_level(book_side, record.price, level_price):
            at_level_total += record.volume
            at_level_last_time = record.event_time
        at_level_cumulative_volume.append(at_level_total)
        at_level_last_times.append(at_level_last_time)

        if trade_reaches_price(book_side, record.price, level_price):
            through_level_total += record.volume
            through_level_last_time = record.event_time
        through_level_cumulative_volume.append(through_level_total)
        through_level_last_times.append(through_level_last_time)

    return TradeEvidenceIndex(
        event_times,
        at_level_cumulative_volume,
        at_level_last_times,
        through_level_cumulative_volume,
        through_level_last_times,
    )


def reduce_ahead_by_trade_volume(order, traded_size):
    if traded_size <= 0 or order.result != -1:
        return
    order.ahead = max(order.ahead - traded_size, 0.0)


def reconcile_same_best_price(
    active_orders,
    size_delta,
    pending_trade_records,
    book_side,
    level_price,
    update_event_time,
):
    if not active_orders:
        return

    evidence_index = build_trade_evidence_index(pending_trade_records, book_side, level_price)
    total_traded_at_level = evidence_index.at_level_after(float("-inf")).volume

    for order in active_orders:
        if order.result != -1:
            continue

        pre_submit_trade = evidence_index.at_level_at_or_before(order.submit_time)
        post_submit_trade = evidence_index.at_level_after(order.submit_time)

        reduce_ahead_by_trade_volume(order, pre_submit_trade.volume)

        if post_submit_trade.volume > 0:
            apply_trade_volume(
                [order],
                post_submit_trade.volume,
                post_submit_trade.last_event_time
                if post_submit_trade.last_event_time is not None
                else update_event_time,
            )

        residual = size_delta + total_traded_at_level
        if not np.isclose(residual, 0.0):
            apply_size_delta([order], residual)


def reconcile_price_change(
    active_orders,
    pending_trade_records,
    book_side,
    level_price,
    update_event_time,
):
    evidence_index = build_trade_evidence_index(pending_trade_records, book_side, level_price)

    for order in active_orders:
        if order.result != -1:
            continue

        traded_through_level = evidence_index.through_level_after(order.submit_time)
        finalize_order(
            order,
            traded_through_level.last_event_time
            if traded_through_level.last_event_time is not None
            else update_event_time,
            1 if traded_through_level.volume > 0 else 0,
        )


def reconcile_one_side(
    book_side,
    orders_by_price,
    previous_best_index,
    previous_best_price,
    previous_best_size,
    current_best_price,
    current_best_size,
    pending_trade_records,
    update_event_time,
):
    if previous_best_index is None or np.isnan(previous_best_price):
        return False

    orders_at_previous_best = get_active_orders_at_index(orders_by_price, previous_best_index)
    best_price_unchanged = same_price(previous_best_price, current_best_price)
    best_size_unchanged = np.isclose(previous_best_size, current_best_size)
    if best_price_unchanged and best_size_unchanged:
        return False

    if best_price_unchanged:
        reconcile_same_best_price(
            orders_at_previous_best,
            current_best_size - previous_best_size,
            pending_trade_records,
            book_side,
            previous_best_price,
            update_event_time,
        )
        return True

    if is_worse_best_price_change(book_side, previous_best_price, current_best_price):
        reconcile_price_change(
            orders_at_previous_best,
            pending_trade_records,
            book_side,
            previous_best_price,
            update_event_time,
        )
        return True

    reconcile_price_change(
        orders_at_previous_best,
        [],
        book_side,
        previous_best_price,
        update_event_time,
    )
    return True


def record_best_quote(quote_timeline, event_time, best_bid_price, best_bid_size, best_ask_price, best_ask_size):
    quote_timeline.append(
        (
            float(event_time),
            float(best_bid_price),
            float(best_bid_size),
            float(best_ask_price),
            float(best_ask_size),
        )
    )


def quote_has_complete_prices(best_bid_price, best_bid_size, best_ask_price, best_ask_size):
    return (
        np.isfinite(best_bid_price)
        and np.isfinite(best_ask_price)
        and best_bid_size > 0
        and best_ask_size > 0
    )


def compute_quote_prices(best_bid_price, best_bid_size, best_ask_price, best_ask_size):
    if not quote_has_complete_prices(best_bid_price, best_bid_size, best_ask_price, best_ask_size):
        return np.nan, np.nan

    mid_price = (best_bid_price + best_ask_price) / 2
    total_size = best_bid_size + best_ask_size
    if total_size <= 0:
        return float(mid_price), np.nan

    micro_price = (best_ask_price * best_bid_size + best_bid_price * best_ask_size) / total_size
    return float(mid_price), float(micro_price)


def get_profit_target_time(order, resolved_time):
    if order.result == 1:
        if not np.isfinite(order.fill_time):
            return np.nan
        return float(order.fill_time + resolved_time)
    if order.result == 0:
        return float(order.submit_time + resolved_time)
    return np.nan


def get_evolved_prices(order, quote_timeline, event_times, resolved_time):
    if not quote_timeline:
        return np.nan, np.nan

    target_time = get_profit_target_time(order, resolved_time)
    if not np.isfinite(target_time):
        return np.nan, np.nan
    quote_position = bisect_right(event_times, target_time) - 1
    if quote_position < 0:
        return np.nan, np.nan
    if target_time > quote_timeline[-1][0]:
        return np.nan, np.nan

    (
        _event_time,
        best_bid_price,
        best_bid_size,
        best_ask_price,
        best_ask_size,
    ) = quote_timeline[quote_position]
    return compute_quote_prices(best_bid_price, best_bid_size, best_ask_price, best_ask_size)


def compute_evolved_metrics(orders, quote_timeline, resolved_time, order_side):
    mid_prices = []
    micro_prices = []
    mid_profits = []
    micro_profits = []
    event_times = [quote[0] for quote in quote_timeline]
    profit_multiplier = -1.0 if order_side == "ask" else 1.0

    for order in orders:
        mid_price, micro_price = get_evolved_prices(
            order,
            quote_timeline,
            event_times,
            resolved_time,
        )
        mid_prices.append(mid_price)
        micro_prices.append(micro_price)
        mid_profit = profit_multiplier * (mid_price - order.price) if np.isfinite(mid_price) else np.nan
        micro_profit = profit_multiplier * (micro_price - order.price) if np.isfinite(micro_price) else np.nan
        mid_profits.append(mid_profit)
        micro_profits.append(micro_profit)

    return (
        np.array(mid_prices, dtype=float),
        np.array(micro_prices, dtype=float),
        np.array(mid_profits, dtype=float),
        np.array(micro_profits, dtype=float),
    )


def compute_quote_buffer_end(order_groups, simulation_end, resolved_time):
    max_fill_time = float(simulation_end)
    for orders in order_groups:
        for order in orders:
            if order.result == 1 and np.isfinite(order.fill_time):
                max_fill_time = max(max_fill_time, float(order.fill_time))
    return max_fill_time + max(resolved_time, 0.0)


def append_quote_timeline_updates(
    quote_timeline,
    events,
    event_index,
    orderbook,
    price_levels,
    best_bid_index,
    best_ask_index,
    end_time,
):
    while event_index < len(events) and events[event_index][0] <= end_time:
        (
            event_time,
            _priority,
            event_type,
            event_price,
            event_volume,
            event_side,
        ) = events[event_index]
        event_index += 1

        if event_type == "trade":
            continue

        updated_index, _updated_value = update_orderbook(
            orderbook,
            price_levels,
            event_price,
            event_volume,
            event_side,
        )
        best_bid_index = advance_best_bid_index(orderbook, updated_index, best_bid_index)
        best_ask_index = advance_best_ask_index(orderbook, updated_index, best_ask_index)
        current_bid_price, current_bid_size, current_ask_price, current_ask_size = get_best_levels_from_indices(
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
        )
        record_best_quote(
            quote_timeline,
            event_time,
            current_bid_price,
            current_bid_size,
            current_ask_price,
            current_ask_size,
        )

    return event_index, best_bid_index, best_ask_index


def finalize_unresolved(
    orders,
    quote_timeline=None,
    resolved_time=DEFAULT_RESOLVED_TIME,
    order_side="bid",
):
    if quote_timeline is None:
        quote_timeline = []

    price = np.array([order.price for order in orders], dtype=float)
    near_size = np.array([order.near_size for order in orders], dtype=float)
    opp_size = np.array([order.opp_size for order in orders], dtype=float)
    survival_time = np.array([order.survival_time for order in orders], dtype=float)
    ahead = np.array([max(order.ahead, 0.0) for order in orders], dtype=float)
    behind = np.array([max(order.behind, 0.0) for order in orders], dtype=float)
    vorder_ratio = np.array([order.vorder_ratio for order in orders], dtype=float)
    result = np.array([order.result for order in orders], dtype=int)
    spread = np.array([order.spread for order in orders], dtype=float)
    return (
        price,
        near_size,
        opp_size,
        survival_time,
        ahead,
        behind,
        vorder_ratio,
        result,
        spread,
        *compute_evolved_metrics(orders, quote_timeline, resolved_time, order_side),
    )


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
        empty_sim.copy(),
        empty_result.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
    )


def simulate_virtual_best_orders(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    price_levels = {level[0] for level in init}
    price_levels.update(update[1] for update in updates)
    price_levels = np.array(sorted(price_levels), dtype=float)

    orderbook = np.zeros(len(price_levels), dtype=float)
    for level in init:
        update_orderbook(orderbook, price_levels, level[0], level[1], level[2])

    best_bid_index, best_ask_index = initialize_best_indices(orderbook)

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

    quote_timeline = []
    initial_bid_price, initial_bid_size, initial_ask_price, initial_ask_size = get_best_levels_from_indices(
        orderbook,
        price_levels,
        best_bid_index,
        best_ask_index,
    )
    record_best_quote(
        quote_timeline,
        orderbook_start_time,
        initial_bid_price,
        initial_bid_size,
        initial_ask_price,
        initial_ask_size,
    )

    events = build_event_stream(updates, trades)
    event_index = 0
    next_submit_time = simulation_start
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders_by_price = {}
    ask_orders_by_price = {}

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

            if event_time > simulation_end:
                event_index -= 1
                break

            best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels_from_indices(
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
            )
            debug_best_state(
                "before_event",
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
                best_bid_price,
                best_bid_size,
                best_ask_price,
                best_ask_size,
                event_time=event_time,
                event_type=event_type,
                event_price=event_price,
                event_volume=event_volume,
                event_side=event_side,
            )

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
            previous_bid_index = best_bid_index
            previous_ask_index = best_ask_index

            updated_index, _updated_value = update_orderbook(
                orderbook,
                price_levels,
                event_price,
                event_volume,
                event_side,
            )
            best_bid_index = advance_best_bid_index(orderbook, updated_index, best_bid_index)
            best_ask_index = advance_best_ask_index(orderbook, updated_index, best_ask_index)

            current_bid_price, current_bid_size, current_ask_price, current_ask_size = get_best_levels_from_indices(
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
            )
            debug_best_state(
                "after_update",
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
                current_bid_price,
                current_bid_size,
                current_ask_price,
                current_ask_size,
                event_time=event_time,
                event_type=event_type,
                event_price=event_price,
                event_volume=event_volume,
                event_side=event_side,
                updated_index=updated_index,
            )
            record_best_quote(
                quote_timeline,
                event_time,
                current_bid_price,
                current_bid_size,
                current_ask_price,
                current_ask_size,
            )

            bid_consumed = reconcile_one_side(
                "bid",
                bid_orders_by_price,
                previous_bid_index,
                previous_bid_price,
                previous_bid_size,
                current_bid_price,
                current_bid_size,
                pending_trade_evidence["bid"],
                event_time,
            )
            ask_consumed = reconcile_one_side(
                "ask",
                ask_orders_by_price,
                previous_ask_index,
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

        best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels_from_indices(
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
        )
        debug_best_state(
            "before_submit",
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
            best_bid_price,
            best_bid_size,
            best_ask_price,
            best_ask_size,
            event_time=next_submit_time,
            event_type="submit",
        )

        bid_order = create_virtual_order(
            best_bid_size,
            best_ask_size,
            compute_bid_ask_spread(best_bid_price, best_ask_price),
            next_submit_time,
            best_bid_price,
            base_tick,
        )
        if bid_order is not None:
            get_orders_bucket(bid_orders_by_price, best_bid_index).append(bid_order)

        ask_order = create_virtual_order(
            best_ask_size,
            best_bid_size,
            compute_bid_ask_spread(best_bid_price, best_ask_price),
            next_submit_time,
            best_ask_price,
            base_tick,
        )
        if ask_order is not None:
            get_orders_bucket(ask_orders_by_price, best_ask_index).append(ask_order)

        next_submit_time += time_step

    bid_orders = [order for bucket in bid_orders_by_price.values() for order in bucket]
    ask_orders = [order for bucket in ask_orders_by_price.values() for order in bucket]

    for order in bid_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)
    for order in ask_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)

    quote_buffer_end = compute_quote_buffer_end(
        (bid_orders, ask_orders),
        simulation_end,
        resolved_time,
    )
    append_quote_timeline_updates(
        quote_timeline,
        events,
        event_index,
        orderbook,
        price_levels,
        best_bid_index,
        best_ask_index,
        quote_buffer_end,
    )

    bid_output = finalize_unresolved(bid_orders, quote_timeline, resolved_time, "bid")
    ask_output = finalize_unresolved(ask_orders, quote_timeline, resolved_time, "ask")
    return (
        *bid_output[:9],
        *ask_output[:9],
        *bid_output[9:],
        *ask_output[9:],
    )

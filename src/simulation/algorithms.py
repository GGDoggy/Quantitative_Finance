from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .core import (
    advance_best_ask_index,
    advance_best_bid_index,
    append_depth_orders_for_side,
    append_quote_timeline_updates,
    append_trade_evidence,
    build_event_stream,
    compute_bid_ask_spread,
    compute_quote_buffer_end,
    debug_best_state,
    empty_outputs,
    finalize_unresolved,
    get_best_levels_from_indices,
    initialize_best_indices,
    reconcile_depth_side,
    record_best_quote,
    side_to_trade_key,
    simulate_virtual_best_orders as simulate_time_averaged_random_cancellation,
    unix_to_daily_seconds,
    update_orderbook,
)


DEFAULT_RESOLVED_TIME = 1.0
TIME_AVERAGED_RANDOM_CANCELLATION_NAME = "time_averaged_random_cancellation"
EVENT_BALANCED_NAME = "event_balanced"
BEST_SIZE_CHANGED_NAME = "best_size_changed"
SimulationAlgorithm = Callable[..., tuple]


def append_new_depth_orders(
    bid_orders_by_price,
    ask_orders_by_price,
    orderbook,
    price_levels,
    best_bid_index,
    best_ask_index,
    best_bid_price,
    best_bid_size,
    best_ask_price,
    best_ask_size,
    submit_time,
    base_tick,
    order_depth=1,
):
    spread = compute_bid_ask_spread(best_bid_price, best_ask_price)
    bid_orders = append_depth_orders_for_side(
        bid_orders_by_price,
        "bid",
        orderbook,
        price_levels,
        best_bid_index,
        best_ask_size,
        spread,
        submit_time,
        base_tick,
        order_depth,
    )
    ask_orders = append_depth_orders_for_side(
        ask_orders_by_price,
        "ask",
        orderbook,
        price_levels,
        best_ask_index,
        best_bid_size,
        spread,
        submit_time,
        base_tick,
        order_depth,
    )
    return bid_orders, ask_orders


def has_more_events_at_time(events, event_index, event_time):
    return event_index < len(events) and events[event_index][0] == event_time


def clamp_unresolved_orders(orders):
    for order in orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)


def _count_unresolved_orders(orders_by_price):
    return sum(order.result == -1 for bucket in orders_by_price.values() for order in bucket)


def _price_changed(previous_price, current_price):
    if np.isnan(previous_price) or np.isnan(current_price):
        return not (np.isnan(previous_price) and np.isnan(current_price))
    return not np.isclose(previous_price, current_price)


def _best_level_changed(previous_price, previous_size, current_price, current_size):
    return _price_changed(previous_price, current_price) or not np.isclose(
        previous_size,
        current_size,
    )


def _append_bid_orders(
    bid_orders_by_price,
    orderbook,
    price_levels,
    best_bid_index,
    best_ask_size,
    event_time,
    best_bid_price,
    best_ask_price,
    base_tick,
    order_depth=1,
):
    return append_depth_orders_for_side(
        bid_orders_by_price,
        "bid",
        orderbook,
        price_levels,
        best_bid_index,
        best_ask_size,
        compute_bid_ask_spread(best_bid_price, best_ask_price),
        event_time,
        base_tick,
        order_depth,
    )


def _append_ask_orders(
    ask_orders_by_price,
    orderbook,
    price_levels,
    best_ask_index,
    best_bid_size,
    event_time,
    best_ask_price,
    best_bid_price,
    base_tick,
    order_depth=1,
):
    return append_depth_orders_for_side(
        ask_orders_by_price,
        "ask",
        orderbook,
        price_levels,
        best_ask_index,
        best_bid_size,
        compute_bid_ask_spread(best_bid_price, best_ask_price),
        event_time,
        base_tick,
        order_depth,
    )


def simulate_best_size_changed(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
    resolved_time=DEFAULT_RESOLVED_TIME,
    order_depth=1,
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
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders_by_price = {}
    ask_orders_by_price = {}
    unresolved_order_counts = {"bid": 0, "ask": 0}
    pending_update_reference = None

    next_submit_time = simulation_start

    while event_index < len(events) or next_submit_time is not None:
        next_event_time = events[event_index][0] if event_index < len(events) else float("inf")
        should_process_event = (
            event_index < len(events)
            and (next_submit_time is None or next_event_time <= next_submit_time)
        )

        if should_process_event:
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
                if event_time <= simulation_start and next_submit_time is not None:
                    continue

                trade_key = side_to_trade_key(event_side)
                if unresolved_order_counts[trade_key] <= 0:
                    pending_trade_evidence[trade_key].clear()
                    continue

                append_trade_evidence(
                    pending_trade_evidence,
                    event_side,
                    event_price,
                    event_volume,
                    event_time,
                )
                continue

            if pending_update_reference is None or pending_update_reference[0] != event_time:
                pending_update_reference = (
                    event_time,
                    best_bid_price,
                    best_bid_size,
                    best_ask_price,
                    best_ask_size,
                    orderbook.copy(),
                )

            updated_index, _updated_value = update_orderbook(orderbook, price_levels, event_price, event_volume, event_side)
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

            if has_more_events_at_time(events, event_index, event_time):
                continue

            record_best_quote(
                quote_timeline,
                event_time,
                current_bid_price,
                current_bid_size,
                current_ask_price,
                current_ask_size,
            )

            (
                _reference_time,
                previous_bid_price,
                previous_bid_size,
                previous_ask_price,
                previous_ask_size,
                previous_orderbook,
            ) = pending_update_reference
            pending_update_reference = None

            bid_consumed = reconcile_depth_side(
                "bid",
                bid_orders_by_price,
                price_levels,
                previous_orderbook,
                orderbook,
                best_bid_index,
                pending_trade_evidence["bid"],
                event_time,
            )
            ask_consumed = reconcile_depth_side(
                "ask",
                ask_orders_by_price,
                price_levels,
                previous_orderbook,
                orderbook,
                best_ask_index,
                pending_trade_evidence["ask"],
                event_time,
            )

            if bid_consumed:
                pending_trade_evidence["bid"].clear()
                unresolved_order_counts["bid"] = _count_unresolved_orders(bid_orders_by_price)
            if ask_consumed:
                pending_trade_evidence["ask"].clear()
                unresolved_order_counts["ask"] = _count_unresolved_orders(ask_orders_by_price)

            if next_submit_time is not None and event_time <= next_submit_time:
                continue

            if event_time < simulation_start:
                continue

            if _best_level_changed(
                previous_bid_price,
                previous_bid_size,
                current_bid_price,
                current_bid_size,
            ):
                debug_best_state(
                    "before_submit",
                    orderbook,
                    price_levels,
                    best_bid_index,
                    best_ask_index,
                    current_bid_price,
                    current_bid_size,
                    current_ask_price,
                    current_ask_size,
                    event_time=event_time,
                    event_type="submit_bid",
                )
                bid_orders = _append_bid_orders(
                    bid_orders_by_price,
                    orderbook,
                    price_levels,
                    best_bid_index,
                    current_ask_size,
                    event_time,
                    current_bid_price,
                    current_ask_price,
                    base_tick,
                    order_depth,
                )
                unresolved_order_counts["bid"] += len(bid_orders)

            if _best_level_changed(
                previous_ask_price,
                previous_ask_size,
                current_ask_price,
                current_ask_size,
            ):
                debug_best_state(
                    "before_submit",
                    orderbook,
                    price_levels,
                    best_bid_index,
                    best_ask_index,
                    current_bid_price,
                    current_bid_size,
                    current_ask_price,
                    current_ask_size,
                    event_time=event_time,
                    event_type="submit_ask",
                )
                ask_orders = _append_ask_orders(
                    ask_orders_by_price,
                    orderbook,
                    price_levels,
                    best_ask_index,
                    current_bid_size,
                    event_time,
                    current_ask_price,
                    current_bid_price,
                    base_tick,
                    order_depth,
                )
                unresolved_order_counts["ask"] += len(ask_orders)

            if next_submit_time is not None and event_time >= next_submit_time:
                next_submit_time = None

            continue

        if next_submit_time is None:
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
        bid_orders, ask_orders = append_new_depth_orders(
            bid_orders_by_price,
            ask_orders_by_price,
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
            best_bid_price,
            best_bid_size,
            best_ask_price,
            best_ask_size,
            next_submit_time,
            base_tick,
            order_depth,
        )
        unresolved_order_counts["bid"] += len(bid_orders)
        unresolved_order_counts["ask"] += len(ask_orders)
        next_submit_time = None

    bid_orders = [order for bucket in bid_orders_by_price.values() for order in bucket]
    ask_orders = [order for bucket in ask_orders_by_price.values() for order in bucket]

    clamp_unresolved_orders(bid_orders)
    clamp_unresolved_orders(ask_orders)

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
        *bid_output[9:13],
        *ask_output[9:13],
        bid_output[13],
        ask_output[13],
    )


def simulate_event_balanced(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
    resolved_time=DEFAULT_RESOLVED_TIME,
    order_depth=1,
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
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders_by_price = {}
    ask_orders_by_price = {}

    active_bid_orders = []
    active_ask_orders = []
    pending_update_reference = None
    next_submit_time = simulation_start

    while event_index < len(events) or next_submit_time is not None:
        next_event_time = events[event_index][0] if event_index < len(events) else float("inf")
        should_process_event = (
            event_index < len(events)
            and (next_submit_time is None or next_event_time <= next_submit_time)
        )

        if should_process_event:
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
                if event_time <= simulation_start and next_submit_time is not None:
                    continue

                trade_key = side_to_trade_key(event_side)
                active_orders = active_bid_orders if trade_key == "bid" else active_ask_orders
                if not any(order.result == -1 for order in active_orders):
                    pending_trade_evidence[trade_key].clear()
                    continue

                append_trade_evidence(
                    pending_trade_evidence,
                    event_side,
                    event_price,
                    event_volume,
                    event_time,
                )
                continue

            if pending_update_reference is None or pending_update_reference[0] != event_time:
                pending_update_reference = (
                    event_time,
                    best_bid_price,
                    best_bid_size,
                    best_ask_price,
                    best_ask_size,
                    orderbook.copy(),
                )

            updated_index, _updated_value = update_orderbook(orderbook, price_levels, event_price, event_volume, event_side)
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

            if has_more_events_at_time(events, event_index, event_time):
                continue

            record_best_quote(
                quote_timeline,
                event_time,
                current_bid_price,
                current_bid_size,
                current_ask_price,
                current_ask_size,
            )

            (
                _reference_time,
                previous_bid_price,
                previous_bid_size,
                previous_ask_price,
                previous_ask_size,
                previous_orderbook,
            ) = pending_update_reference
            pending_update_reference = None

            bid_consumed = reconcile_depth_side(
                "bid",
                bid_orders_by_price,
                price_levels,
                previous_orderbook,
                orderbook,
                best_bid_index,
                pending_trade_evidence["bid"],
                event_time,
            )
            ask_consumed = reconcile_depth_side(
                "ask",
                ask_orders_by_price,
                price_levels,
                previous_orderbook,
                orderbook,
                best_ask_index,
                pending_trade_evidence["ask"],
                event_time,
            )

            if bid_consumed:
                pending_trade_evidence["bid"].clear()
            if ask_consumed:
                pending_trade_evidence["ask"].clear()

            if next_submit_time is not None and event_time <= next_submit_time:
                continue

            if event_time < simulation_start:
                continue

            active_bid_orders = [order for order in active_bid_orders if order.result == -1]
            active_ask_orders = [order for order in active_ask_orders if order.result == -1]

            if not active_bid_orders or not active_ask_orders:
                debug_best_state(
                    "before_submit",
                    orderbook,
                    price_levels,
                    best_bid_index,
                    best_ask_index,
                    current_bid_price,
                    current_bid_size,
                    current_ask_price,
                    current_ask_size,
                    event_time=event_time,
                    event_type="submit",
                )
                spread = compute_bid_ask_spread(current_bid_price, current_ask_price)

            if not active_bid_orders:
                active_bid_orders = append_depth_orders_for_side(
                    bid_orders_by_price,
                    "bid",
                    orderbook,
                    price_levels,
                    best_bid_index,
                    current_ask_size,
                    spread,
                    event_time,
                    base_tick,
                    order_depth,
                )

            if not active_ask_orders:
                active_ask_orders = append_depth_orders_for_side(
                    ask_orders_by_price,
                    "ask",
                    orderbook,
                    price_levels,
                    best_ask_index,
                    current_bid_size,
                    spread,
                    event_time,
                    base_tick,
                    order_depth,
                )

            if next_submit_time is not None and event_time >= next_submit_time:
                next_submit_time = None

            continue

        if next_submit_time is None:
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
        active_bid_orders, active_ask_orders = append_new_depth_orders(
            bid_orders_by_price,
            ask_orders_by_price,
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
            best_bid_price,
            best_bid_size,
            best_ask_price,
            best_ask_size,
            next_submit_time,
            base_tick,
            order_depth,
        )
        next_submit_time = None

    bid_orders = [order for bucket in bid_orders_by_price.values() for order in bucket]
    ask_orders = [order for bucket in ask_orders_by_price.values() for order in bucket]

    clamp_unresolved_orders(bid_orders)
    clamp_unresolved_orders(ask_orders)

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
        *bid_output[9:13],
        *ask_output[9:13],
        bid_output[13],
        ask_output[13],
    )


ALGORITHMS: dict[str, SimulationAlgorithm] = {
    TIME_AVERAGED_RANDOM_CANCELLATION_NAME: simulate_time_averaged_random_cancellation,
    EVENT_BALANCED_NAME: simulate_event_balanced,
    BEST_SIZE_CHANGED_NAME: simulate_best_size_changed,
}


def list_algorithms() -> list[str]:
    return list(ALGORITHMS.keys())


def get_algorithm(name: str) -> SimulationAlgorithm:
    try:
        return ALGORITHMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation algorithm: {name}") from exc

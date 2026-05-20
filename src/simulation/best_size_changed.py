import numpy as np

from .constants import DEFAULT_RESOLVED_TIME
from .algorithm_helpers import (
    append_new_best_orders,
    clamp_unresolved_orders,
    has_more_events_at_time,
)
from ._simulation_core import (
    advance_best_ask_index,
    advance_best_bid_index,
    append_trade_evidence,
    append_quote_timeline_updates,
    build_event_stream,
    compute_quote_buffer_end,
    compute_bid_ask_spread,
    create_virtual_order,
    debug_best_state,
    empty_outputs,
    finalize_unresolved,
    record_best_quote,
    get_best_levels_from_indices,
    get_orders_bucket,
    initialize_best_indices,
    reconcile_one_side,
    side_to_trade_key,
    unix_to_daily_seconds,
    update_orderbook,
)


ALGORITHM_NAME = "best_size_changed"


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


def _append_bid_order(
    bid_orders_by_price,
    best_bid_index,
    best_bid_size,
    best_ask_size,
    event_time,
    best_bid_price,
    best_ask_price,
    base_tick,
):
    bid_order = create_virtual_order(
        best_bid_size,
        best_ask_size,
        compute_bid_ask_spread(best_bid_price, best_ask_price),
        event_time,
        best_bid_price,
        base_tick,
    )
    if bid_order is not None:
        get_orders_bucket(bid_orders_by_price, best_bid_index).append(bid_order)
    return bid_order


def _append_ask_order(
    ask_orders_by_price,
    best_ask_index,
    best_ask_size,
    best_bid_size,
    event_time,
    best_ask_price,
    best_bid_price,
    base_tick,
):
    ask_order = create_virtual_order(
        best_ask_size,
        best_bid_size,
        compute_bid_ask_spread(best_bid_price, best_ask_price),
        event_time,
        best_ask_price,
        base_tick,
    )
    if ask_order is not None:
        get_orders_bucket(ask_orders_by_price, best_ask_index).append(ask_order)
    return ask_order


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
                    best_bid_index,
                    best_ask_index,
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
                previous_bid_index,
                previous_ask_index,
            ) = pending_update_reference
            pending_update_reference = None

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
                bid_order = _append_bid_order(
                    bid_orders_by_price,
                    best_bid_index,
                    current_bid_size,
                    current_ask_size,
                    event_time,
                    current_bid_price,
                    current_ask_price,
                    base_tick,
                )
                if bid_order is not None:
                    unresolved_order_counts["bid"] += 1

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
                ask_order = _append_ask_order(
                    ask_orders_by_price,
                    best_ask_index,
                    current_ask_size,
                    current_bid_size,
                    event_time,
                    current_ask_price,
                    current_bid_price,
                    base_tick,
                )
                if ask_order is not None:
                    unresolved_order_counts["ask"] += 1

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
        bid_order, ask_order = append_new_best_orders(
            bid_orders_by_price,
            ask_orders_by_price,
            best_bid_index,
            best_ask_index,
            best_bid_price,
            best_bid_size,
            best_ask_price,
            best_ask_size,
            next_submit_time,
            base_tick,
        )
        if bid_order is not None:
            unresolved_order_counts["bid"] += 1
        if ask_order is not None:
            unresolved_order_counts["ask"] += 1
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
        *bid_output[9:],
        *ask_output[9:],
    )

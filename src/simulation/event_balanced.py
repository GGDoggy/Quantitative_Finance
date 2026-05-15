import numpy as np

from .time_averaged_random_cancellation import (
    advance_best_ask_index,
    advance_best_bid_index,
    append_trade_evidence,
    build_event_stream,
    compute_bid_ask_spread,
    create_virtual_order,
    debug_best_state,
    empty_outputs,
    finalize_unresolved,
    get_best_levels_from_indices,
    get_orders_bucket,
    initialize_best_indices,
    reconcile_one_side,
    side_to_trade_key,
    unix_to_daily_seconds,
    update_orderbook,
)


ALGORITHM_NAME = "event_balanced"


def _append_new_best_orders(
    bid_orders_by_price,
    ask_orders_by_price,
    best_bid_index,
    best_ask_index,
    best_bid_price,
    best_bid_size,
    best_ask_price,
    best_ask_size,
    submit_time,
    base_tick,
):
    spread = compute_bid_ask_spread(best_bid_price, best_ask_price)
    bid_order = create_virtual_order(
        best_bid_size,
        best_ask_size,
        spread,
        submit_time,
        best_bid_price,
        base_tick,
    )
    if bid_order is not None:
        get_orders_bucket(bid_orders_by_price, best_bid_index).append(bid_order)

    ask_order = create_virtual_order(
        best_ask_size,
        best_bid_size,
        spread,
        submit_time,
        best_ask_price,
        base_tick,
    )
    if ask_order is not None:
        get_orders_bucket(ask_orders_by_price, best_ask_index).append(ask_order)

    return bid_order, ask_order


def _has_more_events_at_time(events, event_index, event_time):
    return event_index < len(events) and events[event_index][0] == event_time


def _clamp_unresolved_orders(orders):
    for order in orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)


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

    events = build_event_stream(updates, trades)
    event_index = 0
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders_by_price = {}
    ask_orders_by_price = {}

    active_bid_order = None
    active_ask_order = None
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
                active_order = active_bid_order if trade_key == "bid" else active_ask_order
                if active_order is None or active_order.result != -1:
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

            if _has_more_events_at_time(events, event_index, event_time):
                continue

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
            if ask_consumed:
                pending_trade_evidence["ask"].clear()

            if next_submit_time is not None and event_time <= next_submit_time:
                continue

            if event_time < simulation_start:
                continue

            if active_bid_order is not None and active_bid_order.result != -1:
                active_bid_order = None
            if active_ask_order is not None and active_ask_order.result != -1:
                active_ask_order = None

            if active_bid_order is None or active_ask_order is None:
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

            if active_bid_order is None:
                spread = compute_bid_ask_spread(current_bid_price, current_ask_price)
                active_bid_order = create_virtual_order(
                    current_bid_size,
                    current_ask_size,
                    spread,
                    event_time,
                    current_bid_price,
                    base_tick,
                )
                if active_bid_order is not None:
                    get_orders_bucket(bid_orders_by_price, best_bid_index).append(active_bid_order)

            if active_ask_order is None:
                active_ask_order = create_virtual_order(
                    current_ask_size,
                    current_bid_size,
                    spread,
                    event_time,
                    current_ask_price,
                    base_tick,
                )
                if active_ask_order is not None:
                    get_orders_bucket(ask_orders_by_price, best_ask_index).append(active_ask_order)

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
        active_bid_order, active_ask_order = _append_new_best_orders(
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
        next_submit_time = None

    bid_orders = [order for bucket in bid_orders_by_price.values() for order in bucket]
    ask_orders = [order for bucket in ask_orders_by_price.values() for order in bucket]

    _clamp_unresolved_orders(bid_orders)
    _clamp_unresolved_orders(ask_orders)

    return (
        *finalize_unresolved(bid_orders),
        *finalize_unresolved(ask_orders),
    )

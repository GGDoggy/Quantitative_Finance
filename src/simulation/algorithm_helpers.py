"""Shared helper functions used by simulation algorithm modules."""

from ._simulation_core import compute_bid_ask_spread, create_virtual_order, get_orders_bucket


def append_new_best_orders(
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
    """Create and append new virtual best bid/ask orders at current top-of-book."""
    spread = compute_bid_ask_spread(best_bid_price, best_ask_price)
    bid_order = create_virtual_order(best_bid_size, best_ask_size, spread, submit_time, best_bid_price, base_tick)
    if bid_order is not None:
        get_orders_bucket(bid_orders_by_price, best_bid_index).append(bid_order)

    ask_order = create_virtual_order(best_ask_size, best_bid_size, spread, submit_time, best_ask_price, base_tick)
    if ask_order is not None:
        get_orders_bucket(ask_orders_by_price, best_ask_index).append(ask_order)

    return bid_order, ask_order


def has_more_events_at_time(events, event_index, event_time):
    """Return True when there are still events at the same timestamp."""
    return event_index < len(events) and events[event_index][0] == event_time


def clamp_unresolved_orders(orders):
    """Clamp unresolved order queue metrics to non-negative values."""
    for order in orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)

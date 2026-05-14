import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.simulation.time_averaged_random_cancellation import (
    TradeEvidence,
    VirtualOrder,
    reconcile_price_change,
    reconcile_same_best_price,
)


def make_order(submit_time=10.0, ahead=10.0, remaining_size=1.0):
    return VirtualOrder(
        submit_time=submit_time,
        price=100.0,
        near_size=ahead,
        opp_size=10.0,
        ahead=ahead,
        behind=0.0,
        vorder_ratio=remaining_size / ahead,
        remaining_size=remaining_size,
    )


def test_same_timestamp_trade_reduces_ahead_without_filling_order():
    order = make_order(ahead=5.0)
    pending_trades = [TradeEvidence(price=100.0, volume=6.0, event_time=10.0)]

    reconcile_same_best_price(
        [order],
        size_delta=-6.0,
        pending_trade_records=pending_trades,
        book_side="bid",
        level_price=100.0,
        update_event_time=11.0,
    )

    assert order.result == -1
    assert order.ahead == 0.0
    assert order.remaining_size == 1.0


def test_pre_submit_trades_reduce_queue_before_post_submit_fill():
    order = make_order(ahead=10.0)
    pending_trades = [
        TradeEvidence(price=100.0, volume=6.0, event_time=9.0),
        TradeEvidence(price=100.0, volume=5.0, event_time=11.0),
    ]

    reconcile_same_best_price(
        [order],
        size_delta=-11.0,
        pending_trade_records=pending_trades,
        book_side="bid",
        level_price=100.0,
        update_event_time=12.0,
    )

    assert order.result == 1
    assert order.survival_time == 1.0
    assert order.ahead == 0.0
    assert order.remaining_size == 0.0


def test_same_timestamp_trade_through_cannot_fill_order_on_price_change():
    order = make_order()
    pending_trades = [TradeEvidence(price=99.0, volume=100.0, event_time=10.0)]

    reconcile_price_change(
        [order],
        pending_trade_records=pending_trades,
        book_side="bid",
        level_price=100.0,
        update_event_time=12.0,
    )

    assert order.result == 0
    assert order.survival_time == 2.0


def test_post_submit_trade_through_fills_order_on_price_change():
    order = make_order()
    pending_trades = [TradeEvidence(price=99.0, volume=100.0, event_time=10.1)]

    reconcile_price_change(
        [order],
        pending_trade_records=pending_trades,
        book_side="bid",
        level_price=100.0,
        update_event_time=12.0,
    )

    assert order.result == 1
    assert order.survival_time == pytest.approx(0.1)

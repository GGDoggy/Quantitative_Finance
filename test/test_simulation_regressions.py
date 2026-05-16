from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.simulation import event_balanced
from src.simulation.time_averaged_random_cancellation import (
    VirtualOrder,
    compute_quote_buffer_end,
    finalize_order,
    simulate_virtual_best_orders as simulate_time_averaged,
)


def test_time_averaged_ignores_post_window_fill_events():
    init = [
        [99.0, 5.0, 1],
        [100.0, 5.0, 1],
        [101.0, 5.0, -1],
    ]
    updates = [
        [1.0, 100.0, 5.0, 1],
        [1.0, 101.0, 5.0, -1],
        [2.2, 100.0, 0.0, 1],
        [3.2, 101.0, 5.0, -1],
    ]
    trades = [
        [1.0, 101.0, 1.0, -1],
        [2.1, 100.0, 10.0, 1],
        [3.05, 101.0, 1.0, -1],
    ]

    result = simulate_time_averaged(
        init,
        updates,
        trades,
        start_time=0,
        time_step=5.0,
        base_tick=1.0,
        resolved_time=1.0,
    )

    bid_result = result[7]
    assert bid_result.tolist() == [-1]


def test_compute_quote_buffer_end_uses_latest_fill_time():
    filled_order = VirtualOrder(
        submit_time=10.0,
        price=100.0,
        near_size=1.0,
        opp_size=1.0,
        spread=1.0,
        ahead=0.0,
        behind=0.0,
        vorder_ratio=1.0,
        remaining_size=0.0,
    )
    finalize_order(filled_order, 12.0, 1)

    quote_buffer_end = compute_quote_buffer_end(([filled_order],), 10.0, 5.0)
    assert quote_buffer_end == 17.0


def test_event_balanced_replaces_ask_without_unbound_local(monkeypatch):
    original_reconcile = event_balanced.reconcile_one_side

    def force_only_ask_fill(
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
        if book_side == "ask":
            for bucket in orders_by_price.values():
                for order in bucket:
                    if order.result == -1:
                        finalize_order(order, update_event_time, 1)
                        return True
        return False

    monkeypatch.setattr(event_balanced, "reconcile_one_side", force_only_ask_fill)

    init = [
        [100.0, 5.0, 1],
        [101.0, 5.0, -1],
    ]
    updates = [
        [0.0, 100.0, 5.0, 1],
        [0.0, 101.0, 5.0, -1],
        [2.0, 101.0, 5.0, -1],
        [4.0, 101.0, 5.0, -1],
    ]
    trades = [
        [0.0, 101.0, 1.0, -1],
        [4.0, 101.0, 1.0, -1],
    ]

    result = event_balanced.simulate_virtual_best_orders(
        init,
        updates,
        trades,
        start_time=0,
        time_step=1.0,
        base_tick=1.0,
        resolved_time=1.0,
    )

    ask_result = result[16]
    assert ask_result.tolist() == [1, -1]

    monkeypatch.setattr(event_balanced, "reconcile_one_side", original_reconcile)

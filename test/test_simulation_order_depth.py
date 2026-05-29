import numpy as np
import pytest

from src.simulation.algorithms import simulate_best_size_changed, simulate_event_balanced
from src.simulation.core import (
    initialize_best_indices,
    iter_ask_depth_levels,
    iter_bid_depth_levels,
    simulate_virtual_best_orders,
    update_orderbook,
)
from src.simulation.models import SimulationRequest
from src.simulation.service import simulate_loaded_data
from src.simulation import LoadedMarketData


def _depth_fixture():
    # side=1 stores bid sizes as negative values; side=-1 stores ask sizes as positive values.
    init = [
        [96.0, 4.0, 1],
        [97.0, 5.0, 1],
        [98.0, 0.0, 1],
        [99.0, 2.0, 1],
        [101.0, 3.0, -1],
        [102.0, 0.0, -1],
        [103.0, 6.0, -1],
        [104.0, 7.0, -1],
    ]
    updates = [
        [0.0, 98.0, 0.0, 1],
        [5.0, 102.0, 0.0, -1],
    ]
    trades = [
        [0.0, 99.0, 0.5, 1],
        [5.0, 101.0, 0.5, -1],
    ]
    return init, updates, trades


def _run_time_averaged(order_depth):
    init, updates, trades = _depth_fixture()
    return simulate_virtual_best_orders(
        init,
        updates,
        trades,
        start_time=0.0,
        time_step=10.0,
        base_tick=0.01,
        resolved_time=1.0,
        order_depth=order_depth,
    )


def test_depth_level_iterators_skip_empty_levels_and_walk_away_from_best():
    init, _updates, _trades = _depth_fixture()
    price_levels = np.array(sorted(level[0] for level in init), dtype=float)
    orderbook = np.zeros(len(price_levels), dtype=float)
    for price, volume, side in init:
        update_orderbook(orderbook, price_levels, price, volume, side)

    best_bid_index, best_ask_index = initialize_best_indices(orderbook)

    bid_levels = list(iter_bid_depth_levels(orderbook, price_levels, best_bid_index, 3))
    ask_levels = list(iter_ask_depth_levels(orderbook, price_levels, best_ask_index, 3))

    assert [(index, price, size) for index, price, size in bid_levels] == [
        (3, 99.0, 2.0),
        (1, 97.0, 5.0),
        (0, 96.0, 4.0),
    ]
    assert [(index, price, size) for index, price, size in ask_levels] == [
        (4, 101.0, 3.0),
        (6, 103.0, 6.0),
        (7, 104.0, 7.0),
    ]


def test_order_depth_one_preserves_best_only_order_creation():
    output = _run_time_averaged(order_depth=1)
    bid_prices = output[0]
    ask_prices = output[9]
    bid_near_size = output[1]
    ask_near_size = output[10]

    assert bid_prices.tolist() == [99.0]
    assert ask_prices.tolist() == [101.0]
    assert bid_near_size.tolist() == [2.0]
    assert ask_near_size.tolist() == [3.0]


def test_order_depth_three_creates_orders_from_best_to_available_depth():
    output = _run_time_averaged(order_depth=3)
    bid_prices = output[0]
    ask_prices = output[9]
    bid_near_size = output[1]
    ask_near_size = output[10]

    assert bid_prices.tolist() == [99.0, 97.0, 96.0]
    assert ask_prices.tolist() == [101.0, 103.0, 104.0]
    assert bid_near_size.tolist() == [2.0, 5.0, 4.0]
    assert ask_near_size.tolist() == [3.0, 6.0, 7.0]


def test_service_passes_order_depth_to_registered_algorithm():
    init, updates, trades = _depth_fixture()
    request = SimulationRequest(
        algorithm="time_averaged_random_cancellation",
        time_step=10.0,
        base_tick=0.01,
        resolved_time=1.0,
        order_depth=3,
    )

    result = simulate_loaded_data(
        LoadedMarketData(init=init, updates=updates, trades=trades, start_time=0.0),
        request,
    )

    assert result.bid_prices.tolist() == [99.0, 97.0, 96.0]
    assert result.ask_prices.tolist() == [101.0, 103.0, 104.0]


@pytest.mark.parametrize("order_depth", [0, -1, 1.5, True])
def test_simulation_request_rejects_non_positive_integer_order_depth(order_depth):
    with pytest.raises(ValueError, match="order_depth"):
        SimulationRequest(
            algorithm="event_balanced",
            time_step=0.01,
            base_tick=1e-8,
            resolved_time=1.0,
            order_depth=order_depth,
        )


def test_event_balanced_accepts_depth_parameter_for_initial_submit():
    init, updates, trades = _depth_fixture()
    output = simulate_event_balanced(
        init,
        updates,
        trades,
        start_time=0.0,
        time_step=10.0,
        base_tick=0.01,
        resolved_time=1.0,
        order_depth=3,
    )

    assert output[0].tolist() == [99.0, 97.0, 96.0]
    assert output[9].tolist() == [101.0, 103.0, 104.0]


def test_best_size_changed_accepts_depth_parameter_for_initial_submit():
    init, updates, trades = _depth_fixture()
    output = simulate_best_size_changed(
        init,
        updates,
        trades,
        start_time=0.0,
        time_step=10.0,
        base_tick=0.01,
        resolved_time=1.0,
        order_depth=3,
    )

    assert output[0].tolist() == [99.0, 97.0, 96.0]
    assert output[9].tolist() == [101.0, 103.0, 104.0]

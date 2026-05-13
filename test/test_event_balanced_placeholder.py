from src.simulation.event_balanced_placeholder import simulate_virtual_best_orders


def test_ignores_pre_submission_trade_evidence():
    init = [
        [100.0, 1.0, 1],
        [101.0, 1.0, -1],
    ]
    updates = [
        [0.0, 99.0, 1.0, 1],
        [2.0, 100.0, 0.0, 1],
        [5.0, 99.0, 1.0, 1],
    ]
    trades = [
        [0.5, 100.0, 2.0, 1],
        [5.0, 101.0, 1.0, -1],
    ]

    result = simulate_virtual_best_orders(
        init,
        updates,
        trades,
        start_time=0.0,
        time_step=1.0,
        base_tick=0.1,
    )

    bid_survival_time = result[3]
    bid_result = result[7]

    assert bid_result[0] == 0
    assert bid_survival_time[0] == 0.5

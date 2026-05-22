from src.simulation.io import SIMULATION_METADATA_KEYS, SIMULATION_RESULT_KEYS, serialize_result_for_npz


def test_simulation_result_keys_snapshot() -> None:
    assert SIMULATION_RESULT_KEYS == (
        "bid_prices",
        "bid_near_size",
        "bid_opp_size",
        "bid_survival_time",
        "bid_ahead",
        "bid_behind",
        "bid_vorder_ratio",
        "bid_result",
        "bid_spread",
        "ask_prices",
        "ask_near_size",
        "ask_opp_size",
        "ask_survival_time",
        "ask_ahead",
        "ask_behind",
        "ask_vorder_ratio",
        "ask_result",
        "ask_spread",
        "bid_mid_price",
        "bid_micro_price",
        "bid_mid_profit",
        "bid_micro_profit",
        "ask_mid_price",
        "ask_micro_price",
        "ask_mid_profit",
        "ask_micro_profit",
    )


def test_simulation_metadata_keys_snapshot() -> None:
    assert SIMULATION_METADATA_KEYS == (
        "algorithm",
        "product_id",
        "file_stem",
        "time_step",
        "base_tick",
        "resolved_time",
    )


def test_serialize_result_for_npz_uses_only_result_keys() -> None:
    payload = serialize_result_for_npz(tuple(range(len(SIMULATION_RESULT_KEYS))))
    assert tuple(payload.keys()) == SIMULATION_RESULT_KEYS

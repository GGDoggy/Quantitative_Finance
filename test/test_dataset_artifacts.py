from pathlib import Path

import numpy as np

from src.dataset_artifacts import (
    build_preprocessed_output_path,
    build_simulation_output_path,
    discover_preprocessed_artifacts,
    discover_simulation_artifacts,
    format_resolved_time,
    format_time_step,
    parse_preprocessed_filename,
    parse_simulation_filename,
)


def test_time_tokens_are_normalized() -> None:
    assert format_time_step(1.0) == "1"
    assert format_time_step(0.0100) == "0.01"
    assert format_resolved_time(1.0) == "1"


def test_build_and_parse_paths_round_trip(tmp_path: Path) -> None:
    preprocessed = build_preprocessed_output_path(
        tmp_path, "ETH-USD", "20260523.120000", 0.01
    )
    simulation = build_simulation_output_path(
        tmp_path, "ETH-USD", "20260523.120000", 0.01, "event_balanced", 1.0
    )

    assert parse_preprocessed_filename(preprocessed.name) is not None
    simulation_metadata = parse_simulation_filename(simulation.name)
    assert simulation_metadata is not None
    assert simulation_metadata.algorithm_name == "event_balanced"
    assert simulation_metadata.resolved_time == 1.0
    assert simulation_metadata.order_depth == 1
    assert "-depth-1-" in simulation.name


def test_discovery_matches_existing_orderbook_and_simulation_files(tmp_path: Path) -> None:
    orderbook_path = build_preprocessed_output_path(
        tmp_path, "ETH-USD", "20260523.120000", 0.01
    )
    np.savez_compressed(
        orderbook_path,
        price_axis=np.array([100.0, 101.0]),
        time_axis=np.array(["2026-05-23T12:00:00"], dtype="datetime64[ns]"),
        data=np.array([[1.0, -1.0]]),
        bid=np.array([100.0]),
        ask=np.array([101.0]),
        available_views=np.array(["orderbook", "trades_scatter"]),
    )
    simulation_path = build_simulation_output_path(
        tmp_path, "ETH-USD", "20260523.120000", 0.01, "event_balanced", 1.0, 3
    )
    np.savez_compressed(
        simulation_path,
        bid_near_size=np.array([1.0]),
        bid_opp_size=np.array([2.0]),
        bid_mid_profit=np.array([0.5]),
        bid_micro_profit=np.array([0.4]),
        bid_result=np.array([1]),
        ask_near_size=np.array([1.1]),
        ask_opp_size=np.array([2.1]),
        ask_mid_profit=np.array([0.6]),
        ask_micro_profit=np.array([0.5]),
        ask_result=np.array([0]),
    )

    preprocessed_artifacts = discover_preprocessed_artifacts(tmp_path)
    simulation_artifacts = discover_simulation_artifacts(
        tmp_path,
        product_id="ETH-USD",
        timestamp="20260523.120000",
        time_step=0.01,
    )

    assert len(preprocessed_artifacts) == 1
    assert preprocessed_artifacts[0].simulation_path == simulation_path
    assert len(simulation_artifacts) == 1
    assert simulation_artifacts[0].path == simulation_path
    assert simulation_artifacts[0].order_depth == 3


def test_parse_legacy_simulation_filename_without_depth() -> None:
    metadata = parse_simulation_filename(
        "ETH-USD-20260523.120000-0.01-resolved-1-simulation-event_balanced.npz"
    )

    assert metadata is not None
    assert metadata.order_depth is None
    assert metadata.algorithm_name == "event_balanced"

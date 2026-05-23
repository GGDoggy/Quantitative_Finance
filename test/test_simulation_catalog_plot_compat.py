from pathlib import Path

import numpy as np

from src.plots.fill_probability import load_simulation_arrays
from src.preprocess.catalog import discover_preprocessed_datasets
from src.simulation.io import SIMULATION_RESULT_KEYS, save_result_file
from src.simulation.models import RawSimulationDataset, SimulationResult


def _build_orderbook_payload(path: Path) -> None:
    np.savez_compressed(
        path,
        available_views=np.array(["orderbook"], dtype=object),
        timestamp=np.array([0.0], dtype=float),
        bid_prices=np.array([1.0], dtype=float),
        bid_sizes=np.array([1.0], dtype=float),
        ask_prices=np.array([1.1], dtype=float),
        ask_sizes=np.array([1.0], dtype=float),
    )


def _build_result() -> SimulationResult:
    arrays = []
    for key in SIMULATION_RESULT_KEYS:
        if key.endswith("_result"):
            arrays.append(np.array([1, 0], dtype=int))
        else:
            arrays.append(np.array([1.0, 2.0], dtype=float))
    return SimulationResult.from_algorithm_output(tuple(arrays))


def test_discover_preprocessed_datasets_detects_simulation_outputs(tmp_path: Path) -> None:
    timestamp = "20240101.010203"
    orderbook_path = tmp_path / f"ETH-USD-{timestamp}-0.01-orderbook_for_plot.npz"
    _build_orderbook_payload(orderbook_path)
    dataset = RawSimulationDataset(
        product_id="ETH-USD",
        timestamp=timestamp,
        file_stem=f"ETH-USD-{timestamp}",
        init_path=tmp_path / f"level2-ETH-USD-init-{timestamp}.csv",
        updates_path=tmp_path / f"level2-ETH-USD-updates-{timestamp}.csv",
        trade_path=tmp_path / f"trade-ETH-USD-{timestamp}.csv",
    )
    simulation_path = tmp_path / f"ETH-USD-{timestamp}-0.01-resolved-1.0-simulation-event_balanced.npz"
    save_result_file(
        simulation_path,
        algorithm_name="event_balanced",
        dataset=dataset,
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
        result=_build_result(),
    )

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    discovered = datasets[0]
    assert discovered.simulation_path == simulation_path
    assert discovered.algorithm_name == "event_balanced"
    assert "fill_probability" in discovered.available_views


def test_fill_probability_reader_accepts_saved_simulation_npz(tmp_path: Path) -> None:
    timestamp = "20240101.010203"
    dataset = RawSimulationDataset(
        product_id="ETH-USD",
        timestamp=timestamp,
        file_stem=f"ETH-USD-{timestamp}",
        init_path=tmp_path / f"level2-ETH-USD-init-{timestamp}.csv",
        updates_path=tmp_path / f"level2-ETH-USD-updates-{timestamp}.csv",
        trade_path=tmp_path / f"trade-ETH-USD-{timestamp}.csv",
    )
    simulation_path = tmp_path / f"ETH-USD-{timestamp}-0.01-resolved-1.0-simulation-event_balanced.npz"
    save_result_file(
        simulation_path,
        algorithm_name="event_balanced",
        dataset=dataset,
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
        result=_build_result(),
    )

    arrays = load_simulation_arrays([simulation_path])

    assert len(arrays) == 6
    assert all(array.shape == (2,) for array in arrays)

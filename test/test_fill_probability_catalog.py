import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.data_catalog import PlotDatasetLocator, discover_preprocessed_datasets
from gui.plots.fill_probability import _simulation_path


TIMESTAMP = "20240101.000000"
PRODUCT = "ETH-USD"


def _write_preprocessed(path: Path) -> None:
    np.savez_compressed(path, available_views=np.array(["orderbook"]))


def _write_simulation(path: Path) -> None:
    np.savez_compressed(
        path,
        bid_near_size=np.array([0.01]),
        bid_opp_size=np.array([0.02]),
        bid_result=np.array([1]),
        ask_near_size=np.array([0.01]),
        ask_opp_size=np.array([0.02]),
        ask_result=np.array([0]),
    )


def test_simulation_path_requires_time_step_simulation_boundary(tmp_path: Path) -> None:
    selected = tmp_path / f"{PRODUCT}-{TIMESTAMP}-1-orderbook_for_plot.npz"
    _write_preprocessed(selected)
    longer_token_sim = tmp_path / f"{PRODUCT}-{TIMESTAMP}-10-simulation-demo.npz"
    _write_simulation(longer_token_sim)

    locator = PlotDatasetLocator(PRODUCT, TIMESTAMP, 1.0, tmp_path, "1", selected)

    try:
        _simulation_path(locator)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("matched a simulation file for a longer time-step token")

    exact_sim = tmp_path / f"{PRODUCT}-{TIMESTAMP}-1-simulation-demo.npz"
    _write_simulation(exact_sim)
    assert _simulation_path(locator) == exact_sim


def test_simulation_path_accepts_scientific_notation_writer_token(tmp_path: Path) -> None:
    preprocessed = tmp_path / f"{PRODUCT}-{TIMESTAMP}-0.00001-orderbook_for_plot.npz"
    simulation = tmp_path / f"{PRODUCT}-{TIMESTAMP}-1e-05-simulation-demo.npz"
    _write_preprocessed(preprocessed)
    _write_simulation(simulation)

    locator = PlotDatasetLocator(
        PRODUCT,
        TIMESTAMP,
        1e-05,
        tmp_path,
        "0.00001",
        preprocessed,
    )

    assert _simulation_path(locator) == simulation


def test_discovered_dataset_advertises_fill_probability_when_simulation_exists(tmp_path: Path) -> None:
    preprocessed = tmp_path / f"{PRODUCT}-{TIMESTAMP}-0.00001-orderbook_for_plot.npz"
    simulation = tmp_path / f"{PRODUCT}-{TIMESTAMP}-1e-05-simulation-demo.npz"
    _write_preprocessed(preprocessed)
    _write_simulation(simulation)

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    assert "fill_probability" in datasets[0].available_views

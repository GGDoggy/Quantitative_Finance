from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.plots.discovery import find_simulation_files as find_plot_simulation_files
from src.plots.fill_probability import _simulation_path
from src.preprocess.catalog import (
    PlotDatasetLocator,
    discover_preprocessed_datasets,
    find_simulation_files,
)
from src.simulation.constants import DEFAULT_RESOLVED_TIME


def _write_orderbook_file(path: Path) -> None:
    np.savez_compressed(
        path,
        price_axis=np.array([100.0]),
        time_axis=np.array([0.0]),
        data=np.array([[1.0]]),
        bid=np.array([100.0]),
        ask=np.array([101.0]),
    )


def test_find_simulation_files_filters_resolved_time_and_algorithm(tmp_path):
    filenames = [
        "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz",
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_a.npz",
        "BTC-USD-20240101.000000-0.1-resolved-10-simulation-algo_a.npz",
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_b.npz",
    ]
    for filename in filenames:
        (tmp_path / filename).touch()

    all_catalog = find_simulation_files(tmp_path, "BTC-USD", "20240101.000000", 0.1)
    resolved_catalog = find_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=5.0,
    )
    filtered_catalog = find_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=5.0,
        algorithm_name="algo_b",
    )

    all_plot = find_plot_simulation_files(tmp_path, "BTC-USD", "20240101.000000", 0.1)
    filtered_plot = find_plot_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=5.0,
        algorithm_name="algo_b",
    )

    assert len(all_catalog) == 4
    assert len(resolved_catalog) == 2
    assert [path.name for path in filtered_catalog] == [
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_b.npz"
    ]
    assert [path.name for path in all_plot] == [path.name for path in all_catalog]
    assert [path.name for path in filtered_plot] == [path.name for path in filtered_catalog]


def test_find_simulation_files_treats_legacy_files_as_default_resolved_time(tmp_path):
    filenames = [
        "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz",
        (
            "BTC-USD-20240101.000000-0.1-resolved-1"
            "-simulation-default_algo.npz"
        ),
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-nondefault_algo.npz",
    ]
    for filename in filenames:
        (tmp_path / filename).touch()

    default_catalog = find_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=DEFAULT_RESOLVED_TIME,
    )
    default_plot = find_plot_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=DEFAULT_RESOLVED_TIME,
    )
    nondefault_catalog = find_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=5.0,
    )

    assert [path.name for path in default_catalog] == [
        "BTC-USD-20240101.000000-0.1-resolved-1-simulation-default_algo.npz",
        "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz",
    ]
    assert [path.name for path in default_plot] == [path.name for path in default_catalog]
    assert [path.name for path in nondefault_catalog] == [
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-nondefault_algo.npz"
    ]


def test_find_simulation_files_supports_zero_resolved_time_tokens(tmp_path):
    filenames = [
        "BTC-USD-20240101.000000-0.1-resolved-0-simulation-zero_algo.npz",
        "BTC-USD-20240101.000000-0.1-resolved-0.0-simulation-zero_decimal_algo.npz",
    ]
    for filename in filenames:
        (tmp_path / filename).touch()

    catalog_matches = find_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=0.0,
    )
    plot_matches = find_plot_simulation_files(
        tmp_path,
        "BTC-USD",
        "20240101.000000",
        0.1,
        resolved_time=0.0,
    )

    expected_names = [
        "BTC-USD-20240101.000000-0.1-resolved-0-simulation-zero_algo.npz",
        "BTC-USD-20240101.000000-0.1-resolved-0.0-simulation-zero_decimal_algo.npz",
    ]
    assert [path.name for path in catalog_matches] == expected_names
    assert [path.name for path in plot_matches] == expected_names


def test_discovery_carries_simulation_metadata_and_fill_probability_filters(tmp_path):
    orderbook_path = tmp_path / "BTC-USD-20240101.000000-0.1-orderbook_for_plot.npz"
    _write_orderbook_file(orderbook_path)

    simulation_names = [
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_a.npz",
        "BTC-USD-20240101.000000-0.1-resolved-10-simulation-algo_a.npz",
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_b.npz",
        "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz",
    ]
    for filename in simulation_names:
        (tmp_path / filename).touch()

    datasets = discover_preprocessed_datasets(tmp_path)
    simulation_datasets = [dataset for dataset in datasets if dataset.simulation_path is not None]
    assert len(simulation_datasets) == 4

    selected_dataset = next(
        dataset
        for dataset in simulation_datasets
        if dataset.resolved_time == 5.0 and dataset.algorithm_name == "algo_a"
    )
    locator = selected_dataset.to_locator(tmp_path)
    assert _simulation_path(locator).name == (
        "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_a.npz"
    )

    ambiguous_locator = PlotDatasetLocator(
        product_id="BTC-USD",
        timestamp="20240101.000000",
        time_step=0.1,
        time_step_token="0.1",
        preprocessed_dir=tmp_path,
    )
    with pytest.raises(FileExistsError, match="Specify a single simulation output"):
        _simulation_path(ambiguous_locator)


def test_simulation_path_uses_legacy_file_for_default_resolved_time(tmp_path):
    legacy_path = tmp_path / "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz"
    legacy_path.touch()

    locator = PlotDatasetLocator(
        product_id="BTC-USD",
        timestamp="20240101.000000",
        time_step=0.1,
        time_step_token="0.1",
        resolved_time=DEFAULT_RESOLVED_TIME,
        preprocessed_dir=tmp_path,
    )

    assert _simulation_path(locator) == legacy_path


def test_simulation_path_supports_zero_resolved_time(tmp_path):
    zero_resolved_path = (
        tmp_path / "BTC-USD-20240101.000000-0.1-resolved-0-simulation-zero_algo.npz"
    )
    zero_resolved_path.touch()

    locator = PlotDatasetLocator(
        product_id="BTC-USD",
        timestamp="20240101.000000",
        time_step=0.1,
        time_step_token="0.1",
        resolved_time=0.0,
        preprocessed_dir=tmp_path,
    )

    assert _simulation_path(locator) == zero_resolved_path


def test_simulation_path_stays_ambiguous_with_legacy_and_default_resolved_matches(tmp_path):
    filenames = [
        "BTC-USD-20240101.000000-0.1-simulation-legacy_algo.npz",
        "BTC-USD-20240101.000000-0.1-resolved-1-simulation-default_algo.npz",
    ]
    for filename in filenames:
        (tmp_path / filename).touch()

    locator = PlotDatasetLocator(
        product_id="BTC-USD",
        timestamp="20240101.000000",
        time_step=0.1,
        time_step_token="0.1",
        resolved_time=DEFAULT_RESOLVED_TIME,
        preprocessed_dir=tmp_path,
    )

    with pytest.raises(FileExistsError, match="Specify a single simulation output"):
        _simulation_path(locator)

from __future__ import annotations

import importlib
from pathlib import Path

from src.preprocess import (
    PlotDatasetLocator,
    PreprocessContext,
    PreprocessedDataset,
    RawBatch,
)
from src.preprocess.catalog import (
    PlotDatasetLocator as CatalogPlotDatasetLocator,
    PreprocessedDataset as CatalogPreprocessedDataset,
    RawBatch as CatalogRawBatch,
)
from src.preprocess.common import PreprocessContext as CommonPreprocessContext


def test_model_aliases_share_identity_between_root_and_legacy_modules():
    assert RawBatch is CatalogRawBatch
    assert PreprocessedDataset is CatalogPreprocessedDataset
    assert PlotDatasetLocator is CatalogPlotDatasetLocator
    assert PreprocessContext is CommonPreprocessContext


def test_model_behavior_regressions_are_preserved(tmp_path):
    raw_batch = RawBatch(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        init_path=tmp_path / "init.csv",
        updates_path=tmp_path / "updates.csv",
        trade_path=tmp_path / "trade.csv",
        is_preprocessed=True,
    )
    assert raw_batch.batch_id == "ETH-USD|20240101.010203"
    assert raw_batch.display_name == "ETH-USD | 2024-01-01 01:02:03 | preprocessed"

    dataset_path = tmp_path / "ETH-USD-20240101.010203-0.01-orderbook_for_plot.npz"
    dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        time_step=0.01,
        path=dataset_path,
        available_views=("orderbook", "fill_probability"),
        time_step_token="0.01",
        resolved_time=1.0,
        resolved_time_token="1",
        algorithm_name="event_balanced",
        simulation_path=tmp_path / "ETH-USD-20240101.010203-0.01-simulation-event_balanced.npz",
    )

    assert dataset.dataset_id == (
        f"{dataset_path}#ETH-USD-20240101.010203-0.01-simulation-event_balanced.npz"
    )
    assert (
        dataset.display_name
        == "ETH-USD | 2024-01-01 01:02:03 | 0.01s | "
        "ETH-USD-20240101.010203-0.01-simulation-event_balanced | "
        "orderbook,fill_probability"
    )

    locator = dataset.to_locator(tmp_path)
    assert locator.base_id == "ETH-USD-20240101.010203-0.01"
    assert locator.path == dataset_path

    synthesized_locator = PlotDatasetLocator(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        time_step=0.01,
        preprocessed_dir=tmp_path,
        time_step_token="0.01",
    )
    assert synthesized_locator.path == dataset_path


def test_key_modules_import_without_preprocess_cycles():
    importlib.import_module("gui.catalog")
    importlib.import_module("src.simulation.service")
    importlib.import_module("src.plots.fill_probability")

from __future__ import annotations

from pathlib import Path

from src.app_plot_registry import (
    get_dataset_plot_types,
    get_product_plot_types,
    supports_plot_type,
)
from src.preprocess.catalog import PreprocessedDataset


def test_market_dataset_capabilities_map_to_market_plots() -> None:
    dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        path=Path("ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"),
        available_views=("orderbook", "trades_scatter", "trade_volume_timeline"),
    )

    assert get_dataset_plot_types(dataset) == (
        "orderbook",
        "trades_scatter",
        "trade_volume_timeline",
    )
    assert supports_plot_type(dataset, "trades_scatter")


def test_simulation_dataset_exposes_simulation_plots_from_dataset_facts() -> None:
    dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        path=Path("ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"),
        available_views=("orderbook",),
        simulation_path=Path(
            "ETH-USD-20240101.000000-0.01-simulation-best_size_changed.npz"
        ),
    )

    plot_types = get_dataset_plot_types(dataset)
    assert "orderbook" in plot_types
    assert "fill_probability" in plot_types
    assert "mid_profit" in plot_types
    assert supports_plot_type(dataset, "micro_fill_probability_cost")


def test_product_plot_types_unions_supported_plots_in_registry_order() -> None:
    market_dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        path=Path("ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"),
        available_views=("orderbook", "trades_scatter"),
    )
    simulation_dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000001",
        time_step=0.01,
        path=Path("ETH-USD-20240101.000001-0.01-orderbook_for_plot.npz"),
        available_views=("orderbook",),
        simulation_path=Path(
            "ETH-USD-20240101.000001-0.01-simulation-best_size_changed.npz"
        ),
    )

    assert get_product_plot_types([market_dataset, simulation_dataset]) == (
        "orderbook",
        "trades_scatter",
        "fill_probability",
        "mid_profit",
        "micro_profit",
        "mid_fill_probability_cost",
        "micro_fill_probability_cost",
    )

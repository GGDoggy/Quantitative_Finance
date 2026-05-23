"""Dashboard-local plot registry and adapters for the current src API surface."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.plotlib import (
    build_fill_probability_view,
    build_micro_cost_fill_probability_view,
    build_micro_profit_view,
    build_mid_cost_fill_probability_view,
    build_mid_profit_view,
    build_orderbook_view,
    build_trade_volume_timeline_view,
    build_trades_scatter_view,
)
from src.plotlib.loaders import (
    load_orderbook_payloads,
    load_simulation_arrays_from_metadata,
    load_trades_payloads,
)
from src.preprocess import PLOT_REGISTRY, PreprocessedDataset


PlotLoader = Callable[[Sequence[PreprocessedDataset]], Any]
PlotBuilder = Callable[..., Any]

SIMULATION_PLOT_TYPES = (
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)

APP_PLOT_LABELS = {
    "orderbook": "Orderbook",
    "trades_scatter": "Trades Scatter",
    "trade_volume_timeline": "Trade Volume Timeline",
    "fill_probability": "Fill Probability",
    "mid_profit": "Mid Profit",
    "micro_profit": "Micro Profit",
    "mid_fill_probability_cost": "Mid Cost Fill Probability",
    "micro_fill_probability_cost": "Micro Cost Fill Probability",
}


@dataclass(frozen=True)
class DashboardPlotSpec:
    plot_type: str
    label: str
    loader: PlotLoader
    builder: PlotBuilder
    required_payload_keys: tuple[str, ...] = ()
    requires_simulation: bool = False


def _dataset_loader_tuples(
    datasets: Sequence[PreprocessedDataset],
) -> list[tuple[Path | str, str, str, float]]:
    return [
        (dataset.path, dataset.product_id, dataset.timestamp, dataset.time_step)
        for dataset in datasets
    ]


def _simulation_paths(datasets: Iterable[PreprocessedDataset]) -> list[Path]:
    paths: list[Path] = []
    for dataset in datasets:
        if dataset.simulation_path is None:
            raise ValueError(
                f"Dataset {dataset.display_name} does not have a simulation artifact."
            )
        paths.append(dataset.simulation_path)
    return paths


APP_PLOT_REGISTRY: dict[str, DashboardPlotSpec] = {
    "orderbook": DashboardPlotSpec(
        plot_type="orderbook",
        label=APP_PLOT_LABELS["orderbook"],
        loader=lambda datasets: load_orderbook_payloads(_dataset_loader_tuples(datasets)),
        builder=build_orderbook_view,
        required_payload_keys=PLOT_REGISTRY["orderbook"].required_payload_keys,
    ),
    "trades_scatter": DashboardPlotSpec(
        plot_type="trades_scatter",
        label=APP_PLOT_LABELS["trades_scatter"],
        loader=lambda datasets: load_trades_payloads(_dataset_loader_tuples(datasets)),
        builder=build_trades_scatter_view,
        required_payload_keys=PLOT_REGISTRY["trades_scatter"].required_payload_keys,
    ),
    "trade_volume_timeline": DashboardPlotSpec(
        plot_type="trade_volume_timeline",
        label=APP_PLOT_LABELS["trade_volume_timeline"],
        loader=lambda datasets: load_trades_payloads(_dataset_loader_tuples(datasets)),
        builder=build_trade_volume_timeline_view,
        required_payload_keys=PLOT_REGISTRY["trade_volume_timeline"].required_payload_keys,
    ),
    "fill_probability": DashboardPlotSpec(
        plot_type="fill_probability",
        label=APP_PLOT_LABELS["fill_probability"],
        loader=lambda datasets: load_simulation_arrays_from_metadata(
            _simulation_paths(datasets)
        ),
        builder=build_fill_probability_view,
        requires_simulation=True,
    ),
    "mid_profit": DashboardPlotSpec(
        plot_type="mid_profit",
        label=APP_PLOT_LABELS["mid_profit"],
        loader=lambda datasets: load_simulation_arrays_from_metadata(
            _simulation_paths(datasets)
        ),
        builder=build_mid_profit_view,
        requires_simulation=True,
    ),
    "micro_profit": DashboardPlotSpec(
        plot_type="micro_profit",
        label=APP_PLOT_LABELS["micro_profit"],
        loader=lambda datasets: load_simulation_arrays_from_metadata(
            _simulation_paths(datasets)
        ),
        builder=build_micro_profit_view,
        requires_simulation=True,
    ),
    "mid_fill_probability_cost": DashboardPlotSpec(
        plot_type="mid_fill_probability_cost",
        label=APP_PLOT_LABELS["mid_fill_probability_cost"],
        loader=lambda datasets: load_simulation_arrays_from_metadata(
            _simulation_paths(datasets)
        ),
        builder=build_mid_cost_fill_probability_view,
        requires_simulation=True,
    ),
    "micro_fill_probability_cost": DashboardPlotSpec(
        plot_type="micro_fill_probability_cost",
        label=APP_PLOT_LABELS["micro_fill_probability_cost"],
        loader=lambda datasets: load_simulation_arrays_from_metadata(
            _simulation_paths(datasets)
        ),
        builder=build_micro_cost_fill_probability_view,
        requires_simulation=True,
    ),
}


def get_dataset_plot_types(dataset: PreprocessedDataset) -> list[str]:
    plot_types = list(dataset.available_views)
    if dataset.simulation_artifact is not None:
        plot_types.extend(SIMULATION_PLOT_TYPES)
    return [plot_type for plot_type in APP_PLOT_REGISTRY if plot_type in plot_types]


def get_product_plot_types(datasets: Sequence[PreprocessedDataset]) -> list[str]:
    available = {
        plot_type
        for dataset in datasets
        for plot_type in get_dataset_plot_types(dataset)
    }
    return [plot_type for plot_type in APP_PLOT_REGISTRY if plot_type in available]


def supports_plot_type(dataset: PreprocessedDataset, plot_type: str) -> bool:
    spec = APP_PLOT_REGISTRY.get(plot_type)
    if spec is None:
        return False
    if spec.requires_simulation:
        return dataset.simulation_artifact is not None
    return plot_type in dataset.available_views


def load_plot_input(plot_type: str, datasets: Sequence[PreprocessedDataset]) -> Any:
    return APP_PLOT_REGISTRY[plot_type].loader(datasets)

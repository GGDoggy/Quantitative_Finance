"""Application-level plot registry and dataset-to-plot capability mapping."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol

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

PayloadType = Literal["orderbook", "trades", "simulation"]


@dataclass(frozen=True)
class SupportsAppPlotDataset(Protocol):
    path: object
    simulation_path: object
    available_views: tuple[str, ...]


@dataclass(frozen=True)
class AppPlotEntry:
    plot_id: str
    label: str
    ui_group: str
    builder: Callable[..., object]
    required_payload_type: PayloadType
    supports_dataset: Callable[[SupportsAppPlotDataset], bool]


def _supports_orderbook(dataset: SupportsAppPlotDataset) -> bool:
    return dataset.path.name.endswith("-orderbook_for_plot.npz")


def _supports_trades(dataset: SupportsAppPlotDataset) -> bool:
    # Trades payload is embedded in the same preprocessed orderbook dataset.
    return _supports_orderbook(dataset)


def _supports_simulation(dataset: SupportsAppPlotDataset) -> bool:
    return dataset.simulation_path is not None


APP_PLOT_REGISTRY: dict[str, AppPlotEntry] = {
    "orderbook": AppPlotEntry(
        plot_id="orderbook",
        label="Orderbook",
        ui_group="Market Data",
        builder=build_orderbook_view,
        required_payload_type="orderbook",
        supports_dataset=_supports_orderbook,
    ),
    "trades_scatter": AppPlotEntry(
        plot_id="trades_scatter",
        label="Trades Scatter",
        ui_group="Market Data",
        builder=build_trades_scatter_view,
        required_payload_type="trades",
        supports_dataset=_supports_trades,
    ),
    "trade_volume_timeline": AppPlotEntry(
        plot_id="trade_volume_timeline",
        label="Trade Volume Timeline",
        ui_group="Market Data",
        builder=build_trade_volume_timeline_view,
        required_payload_type="trades",
        supports_dataset=_supports_trades,
    ),
    "fill_probability": AppPlotEntry(
        plot_id="fill_probability",
        label="Fill Probability",
        ui_group="Simulation",
        builder=build_fill_probability_view,
        required_payload_type="simulation",
        supports_dataset=_supports_simulation,
    ),
    "mid_profit": AppPlotEntry(
        plot_id="mid_profit",
        label="Mid Profit",
        ui_group="Simulation",
        builder=build_mid_profit_view,
        required_payload_type="simulation",
        supports_dataset=_supports_simulation,
    ),
    "micro_profit": AppPlotEntry(
        plot_id="micro_profit",
        label="Micro Profit",
        ui_group="Simulation",
        builder=build_micro_profit_view,
        required_payload_type="simulation",
        supports_dataset=_supports_simulation,
    ),
    "mid_fill_probability_cost": AppPlotEntry(
        plot_id="mid_fill_probability_cost",
        label="Mid Fill Probability > Cost",
        ui_group="Simulation",
        builder=build_mid_cost_fill_probability_view,
        required_payload_type="simulation",
        supports_dataset=_supports_simulation,
    ),
    "micro_fill_probability_cost": AppPlotEntry(
        plot_id="micro_fill_probability_cost",
        label="Micro Fill Probability > Cost",
        ui_group="Simulation",
        builder=build_micro_cost_fill_probability_view,
        required_payload_type="simulation",
        supports_dataset=_supports_simulation,
    ),
}

APP_PLOT_LABELS = {plot_id: entry.label for plot_id, entry in APP_PLOT_REGISTRY.items()}

SIMULATION_PLOT_IDS = (
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)


def get_dataset_plot_types(dataset: SupportsAppPlotDataset) -> tuple[str, ...]:
    dataset_capabilities = set(dataset.available_views)
    return tuple(
        plot_id
        for plot_id, entry in APP_PLOT_REGISTRY.items()
        if entry.supports_dataset(dataset)
        and (plot_id in SIMULATION_PLOT_IDS or plot_id in dataset_capabilities)
    )


def supports_plot_type(dataset: SupportsAppPlotDataset, plot_type: str) -> bool:
    if plot_type not in APP_PLOT_REGISTRY:
        return False
    return plot_type in get_dataset_plot_types(dataset)


def get_product_plot_types(datasets: list[SupportsAppPlotDataset]) -> tuple[str, ...]:
    supported = {
        plot_type
        for dataset in datasets
        for plot_type in get_dataset_plot_types(dataset)
    }
    return tuple(
        plot_id for plot_id in APP_PLOT_REGISTRY if plot_id in supported
    )

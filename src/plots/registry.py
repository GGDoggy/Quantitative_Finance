"""Deprecated shim module for legacy src.plots imports."""

"""Register plot types with their lazy plot and preprocess builders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.preprocess.catalog import PlotDatasetLocator
    from src.plots.settings import PlotRenderOptions
    from src.plots.types import PlotBuilder


PreprocessBuilder = Callable[[object], dict[str, object]]


@dataclass(frozen=True)
class PlotSpec:
    key: str
    label: str
    plot_builder: PlotBuilder
    preprocess_builder: PreprocessBuilder | None
    required_payload_keys: tuple[str, ...]


def build_orderbook_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.orderbook import build_orderbook_view as implementation

    return implementation(locators, render_options=render_options)


def build_trades_scatter_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.trades_scatter import build_trades_scatter_view as implementation

    return implementation(locators, render_options=render_options)


def build_trade_volume_timeline_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.trade_volume_timeline import (
        build_trade_volume_timeline_view as implementation,
    )

    return implementation(locators, render_options=render_options)


def build_fill_probability_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.fill_probability import build_fill_probability_view as implementation

    return implementation(locators, render_options=render_options)


def build_mid_profit_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.profit_heatmap import build_mid_profit_view as implementation

    return implementation(locators, render_options=render_options)


def build_micro_profit_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.profit_heatmap import build_micro_profit_view as implementation

    return implementation(locators, render_options=render_options)


def build_mid_cost_fill_probability_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.cost_fill_probability import (
        build_mid_cost_fill_probability_view as implementation,
    )

    return implementation(locators, render_options=render_options)


def build_micro_cost_fill_probability_view(
    locators: list["PlotDatasetLocator"],
    render_options: "PlotRenderOptions" | None = None,
):
    from src.plots.cost_fill_probability import (
        build_micro_cost_fill_probability_view as implementation,
    )

    return implementation(locators, render_options=render_options)


def build_orderbook_payload(context: object) -> dict[str, object]:
    from src.preprocess.orderbook import build_orderbook_payload as implementation

    return implementation(context)


def build_trades_scatter_payload(context: object) -> dict[str, object]:
    from src.preprocess.trades_scatter import build_trades_scatter_payload as implementation

    return implementation(context)


def build_trade_volume_timeline_payload(context: object) -> dict[str, object]:
    from src.preprocess.trade_volume_timeline import (
        build_trade_volume_timeline_payload as implementation,
    )

    return implementation(context)


PLOT_REGISTRY: dict[str, PlotSpec] = {
    "orderbook": PlotSpec(
        key="orderbook",
        label="Orderbook",
        plot_builder=build_orderbook_view,
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
    ),
    "trades_scatter": PlotSpec(
        key="trades_scatter",
        label="Trades Scatter",
        plot_builder=build_trades_scatter_view,
        preprocess_builder=build_trades_scatter_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "trade_volume_timeline": PlotSpec(
        key="trade_volume_timeline",
        label="Trade Volume Timeline",
        plot_builder=build_trade_volume_timeline_view,
        preprocess_builder=build_trade_volume_timeline_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "fill_probability": PlotSpec(
        key="fill_probability",
        label="Fill Probability",
        plot_builder=build_fill_probability_view,
        preprocess_builder=None,
        required_payload_keys=("__simulation_npz__",),
    ),
    "mid_profit": PlotSpec(
        key="mid_profit",
        label="Mid Profit",
        plot_builder=build_mid_profit_view,
        preprocess_builder=None,
        required_payload_keys=("__simulation_npz__",),
    ),
    "micro_profit": PlotSpec(
        key="micro_profit",
        label="Micro Profit",
        plot_builder=build_micro_profit_view,
        preprocess_builder=None,
        required_payload_keys=("__simulation_npz__",),
    ),
    "mid_fill_probability_cost": PlotSpec(
        key="mid_fill_probability_cost",
        label="Mid Fill Probability > Cost",
        plot_builder=build_mid_cost_fill_probability_view,
        preprocess_builder=None,
        required_payload_keys=("__simulation_npz__",),
    ),
    "micro_fill_probability_cost": PlotSpec(
        key="micro_fill_probability_cost",
        label="Micro Fill Probability > Cost",
        plot_builder=build_micro_cost_fill_probability_view,
        preprocess_builder=None,
        required_payload_keys=("__simulation_npz__",),
    ),
}

PLOT_LABELS = {key: spec.label for key, spec in PLOT_REGISTRY.items()}

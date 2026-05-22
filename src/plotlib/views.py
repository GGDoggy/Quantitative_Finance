from __future__ import annotations

import importlib

from .options import PlotRenderOptions
from .protocols import PlotDatasetLocator


def _legacy_builder(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def build_orderbook_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder("src.plots.orderbook", "build_orderbook_view")
    return implementation(locators, render_options=render_options)


def build_trades_scatter_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.trades_scatter", "build_trades_scatter_view"
    )
    return implementation(locators, render_options=render_options)


def build_trade_volume_timeline_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.trade_volume_timeline", "build_trade_volume_timeline_view"
    )
    return implementation(locators, render_options=render_options)


def build_fill_probability_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.fill_probability", "build_fill_probability_view"
    )
    return implementation(locators, render_options=render_options)


def build_mid_profit_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder("src.plots.profit_heatmap", "build_mid_profit_view")
    return implementation(locators, render_options=render_options)


def build_micro_profit_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.profit_heatmap", "build_micro_profit_view"
    )
    return implementation(locators, render_options=render_options)


def build_mid_cost_fill_probability_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.cost_fill_probability", "build_mid_cost_fill_probability_view"
    )
    return implementation(locators, render_options=render_options)


def build_micro_cost_fill_probability_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
):
    implementation = _legacy_builder(
        "src.plots.cost_fill_probability", "build_micro_cost_fill_probability_view"
    )
    return implementation(locators, render_options=render_options)

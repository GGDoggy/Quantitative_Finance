from __future__ import annotations

from collections.abc import Sequence

from .options import PlotRenderOptions
from .types import OrderbookPayloadV1, SimulationArraysV1, TradesPayloadV1


def build_orderbook_view(
    payloads: list[OrderbookPayloadV1],
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.orderbook import build_orderbook_view as implementation

    return implementation(payloads, render_options=render_options)


def build_trades_scatter_view(
    trade_frames_or_payloads: Sequence[TradesPayloadV1 | object],
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.trades_scatter import build_trades_scatter_view as implementation

    return implementation(
        trade_frames_or_payloads, render_options=render_options
    )


def build_trade_volume_timeline_view(
    trade_frames_or_payloads: Sequence[TradesPayloadV1 | object],
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.trade_volume_timeline import (
        build_trade_volume_timeline_view as implementation,
    )

    return implementation(
        trade_frames_or_payloads, render_options=render_options
    )


def build_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.fill_probability import build_fill_probability_view as implementation

    return implementation(
        simulation_arrays, render_options=render_options
    )


def build_mid_profit_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.profit_heatmap import build_mid_profit_view as implementation

    return implementation(simulation_arrays, render_options=render_options)


def build_micro_profit_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.profit_heatmap import build_micro_profit_view as implementation

    return implementation(
        simulation_arrays, render_options=render_options
    )


def build_mid_cost_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.cost_fill_probability import (
        build_mid_cost_fill_probability_view as implementation,
    )

    return implementation(
        simulation_arrays, render_options=render_options
    )


def build_micro_cost_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
):
    from .renderers.cost_fill_probability import (
        build_micro_cost_fill_probability_view as implementation,
    )

    return implementation(
        simulation_arrays, render_options=render_options
    )

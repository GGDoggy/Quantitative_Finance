from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plotlib.errors import PayloadSchemaVersionError
from src.plotlib.options import PlotRenderOptions, ProfitPlotSettings
from src.plotlib.renderers.simulation_common import (
    apply_square_heatmap_axes,
    bin_edges,
    heatmap_trace,
    shared_sample_count_zmax,
)
from src.plotlib.types import SimulationArraysV1


def compute_profit_grid(
    near_size,
    opp_size,
    profit,
    result,
    bins: int,
    *,
    size_min: float,
    size_max: float,
    use_log_bins: bool,
):
    near_size = np.asarray(near_size, dtype=float)
    opp_size = np.asarray(opp_size, dtype=float)
    profit = np.asarray(profit, dtype=float)
    result = np.asarray(result, dtype=int)

    valid_mask = (
        np.isfinite(near_size)
        & np.isfinite(opp_size)
        & np.isfinite(profit)
        & (result == 1)
    )
    near_size = near_size[valid_mask]
    opp_size = opp_size[valid_mask]
    profit = profit[valid_mask]

    if len(near_size) == 0:
        raise ValueError("No valid orders available for profit plotting.")

    near_edges, opp_edges = bin_edges(
        bins,
        size_min=size_min,
        size_max=size_max,
        use_log_bins=use_log_bins,
    )
    sample_count, _, _ = np.histogram2d(near_size, opp_size, bins=[near_edges, opp_edges])
    profit_sum, _, _ = np.histogram2d(
        near_size,
        opp_size,
        bins=[near_edges, opp_edges],
        weights=profit,
    )
    mean_profit = np.divide(
        profit_sum,
        sample_count,
        out=np.full_like(profit_sum, np.nan, dtype=float),
        where=sample_count > 0,
    )
    return near_edges, opp_edges, mean_profit, sample_count


def _shared_profit_limit(*profit_grids: np.ndarray) -> float | None:
    maxima = []
    for grid in profit_grids:
        finite_values = grid[np.isfinite(grid)]
        if finite_values.size > 0:
            maxima.append(float(np.nanmax(np.abs(finite_values))))
    if not maxima:
        return None
    shared_limit = max(maxima)
    return shared_limit if shared_limit > 0 else None


def _metric_label(metric_key: str) -> str:
    if metric_key == "mid_profit":
        return "Mid Profit"
    if metric_key == "micro_profit":
        return "Micro Profit"
    raise ValueError(f"Unsupported profit metric: {metric_key}")


def _profit_key(side: str, metric_key: str) -> str:
    return f"{side}_{metric_key}"


def _grid_for_side(
    arrays: SimulationArraysV1,
    side: str,
    metric_key: str,
    settings: ProfitPlotSettings,
):
    return compute_profit_grid(
        arrays[f"{side}_near_size"],
        arrays[f"{side}_opp_size"],
        arrays[_profit_key(side, metric_key)],
        arrays[f"{side}_result"],
        settings.axis.shared_bins,
        size_min=settings.axis.size_min,
        size_max=settings.axis.size_max,
        use_log_bins=settings.axis.use_log_bins,
    )


def build_profit_view(
    simulation_arrays: SimulationArraysV1,
    metric_key: str,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    settings = (
        render_options.simulation_heatmap_settings
        if isinstance(
            getattr(render_options, "simulation_heatmap_settings", None),
            ProfitPlotSettings,
        )
        else ProfitPlotSettings()
    )
    if simulation_arrays.get("schema_version") != "1":
        raise PayloadSchemaVersionError(
            "simulation arrays", "1", simulation_arrays.get("schema_version")
        )

    bid_near_edges, bid_opp_edges, bid_profit, bid_sample_count = _grid_for_side(
        simulation_arrays,
        "bid",
        metric_key,
        settings,
    )
    ask_near_edges, ask_opp_edges, ask_profit, ask_sample_count = _grid_for_side(
        simulation_arrays,
        "ask",
        metric_key,
        settings,
    )

    shared_profit_limit = (
        settings.metric_limit.limit
        if not settings.metric_limit.auto
        else _shared_profit_limit(bid_profit, ask_profit)
    )
    shared_count_zmax = (
        settings.sample_count_range.max
        if not settings.sample_count_range.auto
        else shared_sample_count_zmax(bid_sample_count, ask_sample_count)
    )
    count_zmin = (
        settings.sample_count_range.min
        if not settings.sample_count_range.auto
        else 0.0
    )
    metric_label = _metric_label(metric_key)

    figure = make_subplots(
        rows=2,
        cols=2,
        horizontal_spacing=0.08,
        vertical_spacing=0.04,
        subplot_titles=(
            f"Bid Average {metric_label}",
            f"Ask Average {metric_label}",
            "Bid Sample Count",
            "Ask Sample Count",
        ),
    )

    figure.add_trace(
        heatmap_trace(
            bid_near_edges,
            bid_opp_edges,
            bid_profit,
            "RdBu",
            name=f"Bid Average {metric_label}",
            zmin=-shared_profit_limit if shared_profit_limit is not None else None,
            zmax=shared_profit_limit,
            zmid=0.0,
            colorbar_title=metric_label,
            showscale=True,
            colorbar_x=1.01,
            colorbar_y=0.79,
            colorbar_len=0.34,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        heatmap_trace(
            ask_near_edges,
            ask_opp_edges,
            ask_profit,
            "RdBu",
            name=f"Ask Average {metric_label}",
            zmin=-shared_profit_limit if shared_profit_limit is not None else None,
            zmax=shared_profit_limit,
            zmid=0.0,
            showscale=False,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=1,
        col=2,
    )
    figure.add_trace(
        heatmap_trace(
            bid_near_edges,
            bid_opp_edges,
            bid_sample_count,
            "Magma",
            name="Bid Sample Count",
            zmin=count_zmin,
            zmax=shared_count_zmax,
            colorbar_title="Sample Count",
            showscale=True,
            colorbar_x=1.01,
            colorbar_y=0.21,
            colorbar_len=0.34,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        heatmap_trace(
            ask_near_edges,
            ask_opp_edges,
            ask_sample_count,
            "Magma",
            name="Ask Sample Count",
            zmin=count_zmin,
            zmax=shared_count_zmax,
            showscale=False,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=2,
        col=2,
    )

    apply_square_heatmap_axes(figure, settings)
    figure.update_layout(
        title=f"{metric_label} Simulation",
        template="plotly_white",
        autosize=True,
        height=1500,
        margin={"l": 36, "r": 68, "t": 72, "b": 36},
    )
    return figure


def build_mid_profit_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_profit_view(simulation_arrays, "mid_profit", render_options=render_options)


def build_micro_profit_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_profit_view(
        simulation_arrays, "micro_profit", render_options=render_options
    )

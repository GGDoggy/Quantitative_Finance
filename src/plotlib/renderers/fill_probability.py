from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plotlib.errors import PayloadSchemaVersionError
from src.plotlib.options import FillProbabilityPlotSettings, PlotRenderOptions
from src.plotlib.renderers.simulation_common import (
    RESOLVED_ONLY,
    apply_square_heatmap_axes,
    bin_edges,
    heatmap_trace,
    shared_sample_count_zmax,
)
from src.plotlib.types import SimulationArraysV1


def compute_fill_probability_grid(
    near_size,
    opp_size,
    result,
    bins: int,
    *,
    size_min: float,
    size_max: float,
    use_log_bins: bool,
):
    near_size = np.asarray(near_size, dtype=float)
    opp_size = np.asarray(opp_size, dtype=float)
    result = np.asarray(result, dtype=int)

    finite_mask = np.isfinite(near_size) & np.isfinite(opp_size)
    valid_mask = finite_mask & (result != -1) if RESOLVED_ONLY else finite_mask

    near_size = near_size[valid_mask]
    opp_size = opp_size[valid_mask]
    result = result[valid_mask]

    if len(near_size) == 0:
        raise ValueError("No valid orders available for fill probability plotting.")

    near_edges, opp_edges = bin_edges(
        bins,
        size_min=size_min,
        size_max=size_max,
        use_log_bins=use_log_bins,
    )

    total_count, _, _ = np.histogram2d(near_size, opp_size, bins=[near_edges, opp_edges])
    fill_count, _, _ = np.histogram2d(
        near_size[result == 1],
        opp_size[result == 1],
        bins=[near_edges, opp_edges],
    )

    fill_probability = np.divide(
        fill_count,
        total_count,
        out=np.full_like(fill_count, np.nan, dtype=float),
        where=total_count > 0,
    )
    return near_edges, opp_edges, fill_probability, total_count


def _add_grid_traces(
    figure: go.Figure,
    near_size: np.ndarray,
    opp_size: np.ndarray,
    result: np.ndarray,
    *,
    probability_title: str,
    count_title: str,
    probability_col: int,
    count_col: int,
    show_probability_scale: bool,
    show_count_scale: bool,
    probability_colorbar_y: float,
    count_colorbar_y: float,
    probability_zmin: float | None = None,
    probability_zmax: float | None = None,
    count_zmin: float | None = None,
    count_zmax: float | None = None,
    axis_settings: FillProbabilityPlotSettings | None = None,
) -> None:
    settings = axis_settings or FillProbabilityPlotSettings()
    near_edges, opp_edges, fill_probability, sample_count = compute_fill_probability_grid(
        near_size,
        opp_size,
        result,
        settings.axis.shared_bins,
        size_min=settings.axis.size_min,
        size_max=settings.axis.size_max,
        use_log_bins=settings.axis.use_log_bins,
    )

    figure.add_trace(
        heatmap_trace(
            near_edges,
            opp_edges,
            fill_probability,
            "Viridis",
            name=probability_title,
            zmin=probability_zmin,
            zmax=probability_zmax,
            colorbar_title="Fill Probability" if show_probability_scale else None,
            showscale=show_probability_scale,
            colorbar_x=1.01 if show_probability_scale else None,
            colorbar_y=probability_colorbar_y if show_probability_scale else None,
            colorbar_len=0.34 if show_probability_scale else None,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=1,
        col=probability_col,
    )
    figure.add_trace(
        heatmap_trace(
            near_edges,
            opp_edges,
            sample_count,
            "Magma",
            name=count_title,
            zmin=count_zmin,
            zmax=count_zmax,
            colorbar_title="Sample Count" if show_count_scale else None,
            showscale=show_count_scale,
            colorbar_x=1.01 if show_count_scale else None,
            colorbar_y=count_colorbar_y if show_count_scale else None,
            colorbar_len=0.34 if show_count_scale else None,
            use_log_bins=settings.axis.use_log_bins,
        ),
        row=2,
        col=count_col,
    )


def _shared_count_zmax(
    arrays: SimulationArraysV1,
    settings: FillProbabilityPlotSettings,
) -> float | None:
    sample_count_maxima = []
    for prefix in ("bid", "ask"):
        _, _, _, sample_count = compute_fill_probability_grid(
            arrays[f"{prefix}_near_size"],
            arrays[f"{prefix}_opp_size"],
            arrays[f"{prefix}_result"],
            settings.axis.shared_bins,
            size_min=settings.axis.size_min,
            size_max=settings.axis.size_max,
            use_log_bins=settings.axis.use_log_bins,
        )
        if sample_count.size > 0:
            sample_count_maxima.append(float(np.nanmax(sample_count)))

    if not sample_count_maxima:
        return None
    shared_zmax = max(sample_count_maxima)
    return shared_zmax if shared_zmax > 0 else None


def build_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    settings = (
        render_options.simulation_heatmap_settings
        if isinstance(
            getattr(render_options, "simulation_heatmap_settings", None),
            FillProbabilityPlotSettings,
        )
        else FillProbabilityPlotSettings()
    )
    if simulation_arrays.get("schema_version") != "1":
        raise PayloadSchemaVersionError(
            "simulation arrays", "1", simulation_arrays.get("schema_version")
        )

    shared_count_zmax = _shared_count_zmax(simulation_arrays, settings)
    probability_zmin = settings.metric_range.min
    probability_zmax = settings.metric_range.max
    count_zmin = (
        settings.sample_count_range.min
        if not settings.sample_count_range.auto
        else 0.0
    )
    count_zmax = (
        settings.sample_count_range.max
        if not settings.sample_count_range.auto
        else shared_count_zmax
    )

    figure = make_subplots(
        rows=2,
        cols=2,
        horizontal_spacing=0.08,
        vertical_spacing=0.04,
        subplot_titles=(
            "Bid Fill Probability",
            "Ask Fill Probability",
            "Bid Sample Count",
            "Ask Sample Count",
        ),
    )

    _add_grid_traces(
        figure,
        simulation_arrays["bid_near_size"],
        simulation_arrays["bid_opp_size"],
        simulation_arrays["bid_result"],
        probability_title="Bid Fill Probability",
        count_title="Bid Sample Count",
        probability_col=1,
        count_col=1,
        show_probability_scale=True,
        show_count_scale=True,
        probability_colorbar_y=0.79,
        count_colorbar_y=0.21,
        probability_zmin=probability_zmin,
        probability_zmax=probability_zmax,
        count_zmin=count_zmin,
        count_zmax=count_zmax,
        axis_settings=settings,
    )
    _add_grid_traces(
        figure,
        simulation_arrays["ask_near_size"],
        simulation_arrays["ask_opp_size"],
        simulation_arrays["ask_result"],
        probability_title="Ask Fill Probability",
        count_title="Ask Sample Count",
        probability_col=2,
        count_col=2,
        show_probability_scale=False,
        show_count_scale=False,
        probability_colorbar_y=0.79,
        count_colorbar_y=0.21,
        probability_zmin=probability_zmin,
        probability_zmax=probability_zmax,
        count_zmin=count_zmin,
        count_zmax=count_zmax,
        axis_settings=settings,
    )

    apply_square_heatmap_axes(figure, settings)
    figure.update_layout(
        title="Fill Probability Simulation",
        template="plotly_white",
        autosize=True,
        height=1500,
        margin={"l": 36, "r": 68, "t": 72, "b": 36},
    )
    return figure

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.preprocess.catalog import PlotDatasetLocator, find_simulation_files
from src.plots.settings import (
    FillProbabilityPlotSettings,
    PlotRenderOptions,
)


RESOLVED_ONLY = True
SIMULATION_REQUIRED_KEYS = (
    "bid_near_size",
    "bid_opp_size",
    "bid_result",
    "ask_near_size",
    "ask_opp_size",
    "ask_result",
)


def _simulation_path(locator: PlotDatasetLocator) -> Path:
    if locator.simulation_path is not None:
        return locator.simulation_path

    candidates = find_simulation_files(
        locator.preprocessed_dir,
        locator.product_id,
        locator.timestamp,
        locator.time_step,
        locator.time_step_token,
        locator.resolved_time,
        locator.resolved_time_token,
        locator.algorithm_name,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No fill probability simulation file found for {locator.base_id}"
        )

    if len(candidates) > 1:
        candidate_names = ", ".join(path.name for path in candidates)
        raise FileExistsError(
            f"Multiple fill probability simulation files found for "
            f"{locator.base_id}. Specify a single simulation output with "
            f"resolved_time/algorithm metadata or choose an explicit simulation file: "
            f"{candidate_names}"
        )

    return candidates[0]


def load_simulation_arrays(paths: Iterable[Path | str]):
    bid_near_size = []
    bid_opp_size = []
    bid_result = []
    ask_near_size = []
    ask_opp_size = []
    ask_result = []

    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [key for key in SIMULATION_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(
                    f"Simulation file {Path(path).name} is missing required key(s): "
                    f"{', '.join(missing_keys)}"
                )

            bid_near_size.append(np.asarray(data["bid_near_size"], dtype=float))
            bid_opp_size.append(np.asarray(data["bid_opp_size"], dtype=float))
            bid_result.append(np.asarray(data["bid_result"], dtype=int))
            ask_near_size.append(np.asarray(data["ask_near_size"], dtype=float))
            ask_opp_size.append(np.asarray(data["ask_opp_size"], dtype=float))
            ask_result.append(np.asarray(data["ask_result"], dtype=int))

    return (
        np.concatenate(bid_near_size) if bid_near_size else np.array([], dtype=float),
        np.concatenate(bid_opp_size) if bid_opp_size else np.array([], dtype=float),
        np.concatenate(bid_result) if bid_result else np.array([], dtype=int),
        np.concatenate(ask_near_size) if ask_near_size else np.array([], dtype=float),
        np.concatenate(ask_opp_size) if ask_opp_size else np.array([], dtype=float),
        np.concatenate(ask_result) if ask_result else np.array([], dtype=int),
    )


def _bin_edges(
    bins: int, *, size_min: float, size_max: float, use_log_bins: bool
) -> tuple[np.ndarray, np.ndarray]:
    if use_log_bins:
        if size_min <= 0 or size_max <= 0:
            raise ValueError("Log-spaced bins require a strictly positive size range.")
        near_edges = np.geomspace(size_min, size_max, bins + 1)
        opp_edges = np.geomspace(size_min, size_max, bins + 1)
    else:
        near_edges = np.linspace(size_min, size_max, bins + 1)
        opp_edges = np.linspace(size_min, size_max, bins + 1)
    return near_edges, opp_edges


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
    if RESOLVED_ONLY:
        valid_mask = finite_mask & (result != -1)
    else:
        valid_mask = finite_mask

    near_size = near_size[valid_mask]
    opp_size = opp_size[valid_mask]
    result = result[valid_mask]

    if len(near_size) == 0:
        raise ValueError("No valid orders available for fill probability plotting.")

    near_edges, opp_edges = _bin_edges(
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


def _bin_centers(edges: np.ndarray, *, use_log_bins: bool) -> np.ndarray:
    if use_log_bins:
        return np.sqrt(edges[:-1] * edges[1:])
    return (edges[:-1] + edges[1:]) / 2.0


def _heatmap_trace(
    near_edges: np.ndarray,
    opp_edges: np.ndarray,
    values: np.ndarray,
    colorscale: str,
    *,
    name: str,
    zmin: float | None = None,
    zmax: float | None = None,
    colorbar_title: str | None = None,
    showscale: bool = True,
    colorbar_x: float | None = None,
    colorbar_y: float | None = None,
    colorbar_len: float | None = None,
    use_log_bins: bool = True,
) -> go.Heatmap:
    colorbar = None
    if colorbar_title is not None:
        colorbar = {"title": colorbar_title}
        if colorbar_x is not None:
            colorbar["x"] = colorbar_x
        if colorbar_y is not None:
            colorbar["y"] = colorbar_y
        if colorbar_len is not None:
            colorbar["len"] = colorbar_len
        colorbar["thickness"] = 18

    return go.Heatmap(
        x=_bin_centers(near_edges, use_log_bins=use_log_bins),
        y=_bin_centers(opp_edges, use_log_bins=use_log_bins),
        z=values.T,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        name=name,
        showscale=showscale,
        colorbar=colorbar,
        hovertemplate="Near Size=%{x}<br>Opp Size=%{y}<br>%{z}<extra></extra>",
    )


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
        _heatmap_trace(
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
        _heatmap_trace(
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


def _shared_sample_count_zmax(
    *orders: tuple[np.ndarray, np.ndarray, np.ndarray],
    settings: FillProbabilityPlotSettings,
) -> float | None:
    sample_count_maxima = []

    for near_size, opp_size, result in orders:
        _, _, _, sample_count = compute_fill_probability_grid(
            near_size,
            opp_size,
            result,
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
    if shared_zmax <= 0:
        return None

    return shared_zmax


def build_fill_probability_view(
    locators: list[PlotDatasetLocator],
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
    simulation_paths = [_simulation_path(locator) for locator in locators]
    (
        bid_near_size,
        bid_opp_size,
        bid_result,
        ask_near_size,
        ask_opp_size,
        ask_result,
    ) = load_simulation_arrays(simulation_paths)

    shared_count_zmax = _shared_sample_count_zmax(
        (bid_near_size, bid_opp_size, bid_result),
        (ask_near_size, ask_opp_size, ask_result),
        settings=settings,
    )
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
        bid_near_size,
        bid_opp_size,
        bid_result,
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
        ask_near_size,
        ask_opp_size,
        ask_result,
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

    for row in (1, 2):
        for col in (1, 2):
            figure.update_xaxes(title_text="Near Size", row=row, col=col)
            figure.update_yaxes(title_text="Opp Size", row=row, col=col)
            if settings.axis.use_log_bins:
                figure.update_xaxes(type="log", row=row, col=col)
                figure.update_yaxes(type="log", row=row, col=col)
            # Keep both axes on the same visual scale so each heatmap bin renders square.
            figure.update_xaxes(constrain="domain", row=row, col=col)
            figure.update_yaxes(
                constrain="domain",
                scaleanchor=f"x{'' if (row, col) == (1, 1) else (row - 1) * 2 + col}",
                scaleratio=1,
                row=row,
                col=col,
            )

    figure.update_layout(
        title="Fill Probability Simulation",
        template="plotly_white",
        autosize=True,
        height=1500,
        margin={"l": 36, "r": 68, "t": 72, "b": 36},
    )
    return figure

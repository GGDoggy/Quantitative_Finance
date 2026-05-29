from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .errors import PayloadSchemaVersionError
from .options import (
    ConditionalFillProbabilityPlotSettings,
    FillProbabilityPlotSettings,
    PlotRenderOptions,
    ProfitPlotSettings,
)
from .types import SimulationArraysV1, normalize_simulation_arrays_to_v1


SIMULATION_REQUIRED_KEYS = (
    "bid_depth",
    "bid_near_size",
    "bid_opp_size",
    "bid_mid_profit",
    "bid_micro_profit",
    "bid_result",
    "ask_depth",
    "ask_near_size",
    "ask_opp_size",
    "ask_mid_profit",
    "ask_micro_profit",
    "ask_result",
)
RESOLVED_ONLY = True


def load_simulation_arrays(paths: Iterable[Path | str]):
    chunks = {key: [] for key in SIMULATION_REQUIRED_KEYS}

    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [
                key
                for key in SIMULATION_REQUIRED_KEYS
                if key not in {"bid_depth", "ask_depth"} and key not in data.files
            ]
            if missing_keys:
                raise KeyError(f"Simulation file {Path(path).name} is missing required key(s): {', '.join(missing_keys)}")
            bid_near_size = np.asarray(data["bid_near_size"], dtype=float)
            ask_near_size = np.asarray(data["ask_near_size"], dtype=float)
            if "bid_depth" in data.files:
                bid_depth = np.asarray(data["bid_depth"], dtype=int)
            else:
                fallback_depth = int(np.asarray(data["depth"]).item()) if "depth" in data.files else 0
                bid_depth = np.full(bid_near_size.shape, fallback_depth, dtype=int)
            if "ask_depth" in data.files:
                ask_depth = np.asarray(data["ask_depth"], dtype=int)
            else:
                fallback_depth = int(np.asarray(data["depth"]).item()) if "depth" in data.files else 0
                ask_depth = np.full(ask_near_size.shape, fallback_depth, dtype=int)
            chunks["bid_depth"].append(bid_depth)
            chunks["bid_near_size"].append(bid_near_size)
            chunks["bid_opp_size"].append(np.asarray(data["bid_opp_size"], dtype=float))
            chunks["bid_mid_profit"].append(np.asarray(data["bid_mid_profit"], dtype=float))
            chunks["bid_micro_profit"].append(np.asarray(data["bid_micro_profit"], dtype=float))
            chunks["bid_result"].append(np.asarray(data["bid_result"], dtype=int))
            chunks["ask_depth"].append(ask_depth)
            chunks["ask_near_size"].append(ask_near_size)
            chunks["ask_opp_size"].append(np.asarray(data["ask_opp_size"], dtype=float))
            chunks["ask_mid_profit"].append(np.asarray(data["ask_mid_profit"], dtype=float))
            chunks["ask_micro_profit"].append(np.asarray(data["ask_micro_profit"], dtype=float))
            chunks["ask_result"].append(np.asarray(data["ask_result"], dtype=int))

    return normalize_simulation_arrays_to_v1(
        {
            "bid_depth": np.concatenate(chunks["bid_depth"]) if chunks["bid_depth"] else np.array([], dtype=int),
            "bid_near_size": np.concatenate(chunks["bid_near_size"]) if chunks["bid_near_size"] else np.array([], dtype=float),
            "bid_opp_size": np.concatenate(chunks["bid_opp_size"]) if chunks["bid_opp_size"] else np.array([], dtype=float),
            "bid_mid_profit": np.concatenate(chunks["bid_mid_profit"]) if chunks["bid_mid_profit"] else np.array([], dtype=float),
            "bid_micro_profit": np.concatenate(chunks["bid_micro_profit"]) if chunks["bid_micro_profit"] else np.array([], dtype=float),
            "bid_result": np.concatenate(chunks["bid_result"]) if chunks["bid_result"] else np.array([], dtype=int),
            "ask_depth": np.concatenate(chunks["ask_depth"]) if chunks["ask_depth"] else np.array([], dtype=int),
            "ask_near_size": np.concatenate(chunks["ask_near_size"]) if chunks["ask_near_size"] else np.array([], dtype=float),
            "ask_opp_size": np.concatenate(chunks["ask_opp_size"]) if chunks["ask_opp_size"] else np.array([], dtype=float),
            "ask_mid_profit": np.concatenate(chunks["ask_mid_profit"]) if chunks["ask_mid_profit"] else np.array([], dtype=float),
            "ask_micro_profit": np.concatenate(chunks["ask_micro_profit"]) if chunks["ask_micro_profit"] else np.array([], dtype=float),
            "ask_result": np.concatenate(chunks["ask_result"]) if chunks["ask_result"] else np.array([], dtype=int),
        }
    )


def load_simulation_arrays_from_metadata(
    simulation_paths: Iterable[Path | str],
):
    return load_simulation_arrays(simulation_paths)


def filter_simulation_arrays_by_depth(
    simulation_arrays: SimulationArraysV1,
    selected_depth: int | None,
) -> SimulationArraysV1:
    if selected_depth is None:
        return simulation_arrays

    filtered: dict[str, np.ndarray | str] = {
        "schema_version": simulation_arrays["schema_version"]
    }
    for side in ("bid", "ask"):
        depth_key = f"{side}_depth"
        side_mask = np.asarray(simulation_arrays[depth_key], dtype=int) == selected_depth
        for key, values in simulation_arrays.items():
            if key == "schema_version" or not key.startswith(f"{side}_"):
                continue
            filtered[key] = np.asarray(values)[side_mask]
    return normalize_simulation_arrays_to_v1(filtered)


def bin_edges(
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


def bin_centers(edges: np.ndarray, *, use_log_bins: bool) -> np.ndarray:
    if use_log_bins:
        return np.sqrt(edges[:-1] * edges[1:])
    return (edges[:-1] + edges[1:]) / 2.0


def heatmap_trace(
    near_edges: np.ndarray,
    opp_edges: np.ndarray,
    values: np.ndarray,
    colorscale: str,
    *,
    name: str,
    zmin: float | None = None,
    zmax: float | None = None,
    zmid: float | None = None,
    colorbar_title: str | None = None,
    showscale: bool = True,
    colorbar_x: float | None = None,
    colorbar_y: float | None = None,
    colorbar_len: float | None = None,
    use_log_bins: bool = True,
) -> go.Heatmap:
    colorbar = None
    if colorbar_title is not None:
        colorbar = {"title": colorbar_title, "thickness": 18}
        if colorbar_x is not None:
            colorbar["x"] = colorbar_x
        if colorbar_y is not None:
            colorbar["y"] = colorbar_y
        if colorbar_len is not None:
            colorbar["len"] = colorbar_len

    return go.Heatmap(
        x=bin_centers(near_edges, use_log_bins=use_log_bins),
        y=bin_centers(opp_edges, use_log_bins=use_log_bins),
        z=values.T,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        zmid=zmid,
        name=name,
        showscale=showscale,
        colorbar=colorbar,
        hovertemplate="Near Size=%{x}<br>Opp Size=%{y}<br>%{z}<extra></extra>",
    )


def shared_sample_count_zmax(*sample_counts: np.ndarray) -> float | None:
    maxima = []
    for sample_count in sample_counts:
        finite_values = sample_count[np.isfinite(sample_count)]
        if finite_values.size > 0:
            maxima.append(float(np.nanmax(finite_values)))
    if not maxima:
        return None
    shared_limit = max(maxima)
    if shared_limit <= 0:
        return None
    return shared_limit


def apply_square_heatmap_axes(figure, settings) -> None:
    for row in (1, 2):
        for col in (1, 2):
            figure.update_xaxes(title_text="Near Size", row=row, col=col)
            figure.update_yaxes(title_text="Opp Size", row=row, col=col)
            if settings.axis.use_log_bins:
                figure.update_xaxes(type="log", row=row, col=col)
                figure.update_yaxes(type="log", row=row, col=col)
            figure.update_xaxes(constrain="domain", row=row, col=col)
            figure.update_yaxes(
                constrain="domain",
                scaleanchor=f"x{'' if (row, col) == (1, 1) else (row - 1) * 2 + col}",
                scaleratio=1,
                row=row,
                col=col,
            )


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


def _add_fill_probability_traces(
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
    simulation_arrays = filter_simulation_arrays_by_depth(
        simulation_arrays,
        render_options.simulation_depth if render_options is not None else None,
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

    _add_fill_probability_traces(
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
    _add_fill_probability_traces(
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
    simulation_arrays = filter_simulation_arrays_by_depth(
        simulation_arrays,
        render_options.simulation_depth if render_options is not None else None,
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


def compute_cost_filtered_fill_probability_grid(
    near_size,
    opp_size,
    result,
    profit,
    bins: int,
    cost: float,
    *,
    size_min: float,
    size_max: float,
    use_log_bins: bool,
):
    near_size = np.asarray(near_size, dtype=float)
    opp_size = np.asarray(opp_size, dtype=float)
    result = np.asarray(result, dtype=int)
    profit = np.asarray(profit, dtype=float)

    finite_mask = np.isfinite(near_size) & np.isfinite(opp_size) & np.isfinite(profit)
    valid_mask = finite_mask & (result != -1) if RESOLVED_ONLY else finite_mask

    profit_mask = valid_mask & (profit > cost)
    near_size = near_size[profit_mask]
    opp_size = opp_size[profit_mask]
    result = result[profit_mask]

    if len(near_size) == 0:
        raise ValueError(
            "No valid orders available for fill probability plotting after applying "
            "the profit > cost filter."
        )

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


def _conditional_metric_label(metric_key: str) -> str:
    if metric_key == "mid_profit":
        return "Mid"
    if metric_key == "micro_profit":
        return "Micro"
    raise ValueError(f"Unsupported profit metric: {metric_key}")


def _conditional_grid_for_side(
    arrays: SimulationArraysV1,
    side: str,
    metric_key: str,
    cost: float,
    settings: ConditionalFillProbabilityPlotSettings,
):
    return compute_cost_filtered_fill_probability_grid(
        arrays[f"{side}_near_size"],
        arrays[f"{side}_opp_size"],
        arrays[f"{side}_result"],
        arrays[f"{side}_{metric_key}"],
        settings.axis.shared_bins,
        cost,
        size_min=settings.axis.size_min,
        size_max=settings.axis.size_max,
        use_log_bins=settings.axis.use_log_bins,
    )


def build_cost_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    metric_key: str,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    cost = render_options.cost if render_options is not None else None
    if cost is None:
        raise ValueError("Cost is required for cost-filtered fill probability plots.")
    settings = (
        render_options.simulation_heatmap_settings
        if isinstance(
            getattr(render_options, "simulation_heatmap_settings", None),
            ConditionalFillProbabilityPlotSettings,
        )
        else ConditionalFillProbabilityPlotSettings()
    )
    if simulation_arrays.get("schema_version") != "1":
        raise PayloadSchemaVersionError(
            "simulation arrays", "1", simulation_arrays.get("schema_version")
        )
    simulation_arrays = filter_simulation_arrays_by_depth(
        simulation_arrays,
        render_options.simulation_depth if render_options is not None else None,
    )

    bid_near_edges, bid_opp_edges, bid_probability, bid_sample_count = _conditional_grid_for_side(
        simulation_arrays,
        "bid",
        metric_key,
        cost,
        settings,
    )
    ask_near_edges, ask_opp_edges, ask_probability, ask_sample_count = _conditional_grid_for_side(
        simulation_arrays,
        "ask",
        metric_key,
        cost,
        settings,
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
    metric_label = _conditional_metric_label(metric_key)

    figure = make_subplots(
        rows=2,
        cols=2,
        horizontal_spacing=0.08,
        vertical_spacing=0.04,
        subplot_titles=(
            f"Bid {metric_label} Fill Probability > Cost",
            f"Ask {metric_label} Fill Probability > Cost",
            "Bid Sample Count",
            "Ask Sample Count",
        ),
    )

    figure.add_trace(
        heatmap_trace(
            bid_near_edges,
            bid_opp_edges,
            bid_probability,
            "Viridis",
            name=f"Bid {metric_label} Fill Probability > Cost",
            zmin=settings.metric_range.min,
            zmax=settings.metric_range.max,
            colorbar_title="Fill Probability",
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
            ask_probability,
            "Viridis",
            name=f"Ask {metric_label} Fill Probability > Cost",
            zmin=settings.metric_range.min,
            zmax=settings.metric_range.max,
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
    cost_token = format(cost, "g")
    figure.update_layout(
        title=f"{metric_label} Fill Probability with Profit > Cost ({cost_token})",
        template="plotly_white",
        autosize=True,
        height=1500,
        margin={"l": 36, "r": 68, "t": 72, "b": 36},
    )
    return figure


def build_mid_cost_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_cost_fill_probability_view(
        simulation_arrays,
        "mid_profit",
        render_options=render_options,
    )


def build_micro_cost_fill_probability_view(
    simulation_arrays: SimulationArraysV1,
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_cost_fill_probability_view(
        simulation_arrays,
        "micro_profit",
        render_options=render_options,
    )

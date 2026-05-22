from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plots.fill_probability import _simulation_path, _heatmap_trace
from src.plots.profit_heatmap import load_simulation_arrays
from src.plotlib.errors import PayloadSchemaVersionError
from src.plots.settings import (
    ConditionalFillProbabilityPlotSettings,
    PlotRenderOptions,
)
from src.plots.types import PlotDatasetLocator


RESOLVED_ONLY = True


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
    if RESOLVED_ONLY:
        valid_mask = finite_mask & (result != -1)
    else:
        valid_mask = finite_mask

    profit_mask = valid_mask & (profit > cost)
    near_size = near_size[profit_mask]
    opp_size = opp_size[profit_mask]
    result = result[profit_mask]

    if len(near_size) == 0:
        raise ValueError(
            "No valid orders available for fill probability plotting after applying "
            "the profit > cost filter."
        )

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


def _metric_label(metric_key: str) -> str:
    if metric_key == "mid_profit":
        return "Mid"
    if metric_key == "micro_profit":
        return "Micro"
    raise ValueError(f"Unsupported profit metric: {metric_key}")


def _shared_sample_count_zmax(*sample_counts: np.ndarray) -> float | None:
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


def _grid_for_side(
    arrays: dict[str, np.ndarray],
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


def _load_arrays(paths: Iterable[Path | str]) -> dict[str, np.ndarray]:
    arrays = load_simulation_arrays(paths)
    if arrays.get("schema_version") != "1":
        raise PayloadSchemaVersionError("simulation arrays", "1", arrays.get("schema_version"))
    result_arrays = {
        "bid_result": [],
        "ask_result": [],
    }

    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            for side in ("bid", "ask"):
                key = f"{side}_result"
                if key not in data.files:
                    raise KeyError(
                        f"Simulation file {Path(path).name} is missing required key(s): "
                        f"{key}"
                    )
                result_arrays[key].append(np.asarray(data[key], dtype=int))

    arrays.update(
        {
            key: np.concatenate(values) if values else np.array([], dtype=int)
            for key, values in result_arrays.items()
        }
    )
    return arrays


def build_cost_fill_probability_view(
    locators: list[PlotDatasetLocator],
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
    simulation_paths = [_simulation_path(locator) for locator in locators]
    arrays = _load_arrays(simulation_paths)

    bid_near_edges, bid_opp_edges, bid_probability, bid_sample_count = _grid_for_side(
        arrays,
        "bid",
        metric_key,
        cost,
        settings,
    )
    ask_near_edges, ask_opp_edges, ask_probability, ask_sample_count = _grid_for_side(
        arrays,
        "ask",
        metric_key,
        cost,
        settings,
    )
    shared_count_zmax = (
        settings.sample_count_range.max
        if not settings.sample_count_range.auto
        else _shared_sample_count_zmax(bid_sample_count, ask_sample_count)
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
            f"Bid {metric_label} Fill Probability > Cost",
            f"Ask {metric_label} Fill Probability > Cost",
            "Bid Sample Count",
            "Ask Sample Count",
        ),
    )

    figure.add_trace(
        _heatmap_trace(
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
        _heatmap_trace(
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
        _heatmap_trace(
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
        _heatmap_trace(
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
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_cost_fill_probability_view(
        locators,
        "mid_profit",
        render_options=render_options,
    )


def build_micro_cost_fill_probability_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_cost_fill_probability_view(
        locators,
        "micro_profit",
        render_options=render_options,
    )

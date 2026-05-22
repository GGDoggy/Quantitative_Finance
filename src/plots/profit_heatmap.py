from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plots.fill_probability import _simulation_path
from src.plotlib.errors import PayloadSchemaVersionError
from src.plotlib.types import normalize_simulation_arrays_to_v1
from src.plots.settings import PlotRenderOptions, ProfitPlotSettings
from src.plots.types import PlotDatasetLocator


SIMULATION_REQUIRED_KEYS = (
    "bid_near_size",
    "bid_opp_size",
    "bid_mid_profit",
    "bid_result",
    "ask_near_size",
    "ask_opp_size",
    "ask_mid_profit",
    "bid_micro_profit",
    "ask_micro_profit",
    "ask_result",
)


def load_simulation_arrays(paths: Iterable[Path | str]):
    bid_near_size = []
    bid_opp_size = []
    bid_mid_profit = []
    bid_micro_profit = []
    bid_result = []
    ask_near_size = []
    ask_opp_size = []
    ask_mid_profit = []
    ask_micro_profit = []
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
            bid_mid_profit.append(np.asarray(data["bid_mid_profit"], dtype=float))
            bid_micro_profit.append(np.asarray(data["bid_micro_profit"], dtype=float))
            bid_result.append(np.asarray(data["bid_result"], dtype=int))
            ask_near_size.append(np.asarray(data["ask_near_size"], dtype=float))
            ask_opp_size.append(np.asarray(data["ask_opp_size"], dtype=float))
            ask_mid_profit.append(np.asarray(data["ask_mid_profit"], dtype=float))
            ask_micro_profit.append(np.asarray(data["ask_micro_profit"], dtype=float))
            ask_result.append(np.asarray(data["ask_result"], dtype=int))

    return normalize_simulation_arrays_to_v1({
        "bid_near_size": (
            np.concatenate(bid_near_size) if bid_near_size else np.array([], dtype=float)
        ),
        "bid_opp_size": (
            np.concatenate(bid_opp_size) if bid_opp_size else np.array([], dtype=float)
        ),
        "bid_mid_profit": (
            np.concatenate(bid_mid_profit)
            if bid_mid_profit
            else np.array([], dtype=float)
        ),
        "bid_micro_profit": (
            np.concatenate(bid_micro_profit)
            if bid_micro_profit
            else np.array([], dtype=float)
        ),
        "bid_result": (
            np.concatenate(bid_result) if bid_result else np.array([], dtype=int)
        ),
        "ask_near_size": (
            np.concatenate(ask_near_size) if ask_near_size else np.array([], dtype=float)
        ),
        "ask_opp_size": (
            np.concatenate(ask_opp_size) if ask_opp_size else np.array([], dtype=float)
        ),
        "ask_mid_profit": (
            np.concatenate(ask_mid_profit)
            if ask_mid_profit
            else np.array([], dtype=float)
        ),
        "ask_micro_profit": (
            np.concatenate(ask_micro_profit)
            if ask_micro_profit
            else np.array([], dtype=float)
        ),
        "ask_result": (
            np.concatenate(ask_result) if ask_result else np.array([], dtype=int)
        ),
    })


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

    near_edges, opp_edges = _bin_edges(
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
        x=_bin_centers(near_edges, use_log_bins=use_log_bins),
        y=_bin_centers(opp_edges, use_log_bins=use_log_bins),
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


def _shared_profit_limit(*profit_grids: np.ndarray) -> float | None:
    maxima = []
    for grid in profit_grids:
        finite_values = grid[np.isfinite(grid)]
        if finite_values.size > 0:
            maxima.append(float(np.nanmax(np.abs(finite_values))))
    if not maxima:
        return None
    shared_limit = max(maxima)
    if shared_limit <= 0:
        return None
    return shared_limit


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


def _metric_label(metric_key: str) -> str:
    if metric_key == "mid_profit":
        return "Mid Profit"
    if metric_key == "micro_profit":
        return "Micro Profit"
    raise ValueError(f"Unsupported profit metric: {metric_key}")


def _profit_key(side: str, metric_key: str) -> str:
    return f"{side}_{metric_key}"


def _grid_for_side(
    arrays: dict[str, np.ndarray],
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
    locators: list[PlotDatasetLocator],
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
    simulation_paths = [_simulation_path(locator) for locator in locators]
    arrays = load_simulation_arrays(simulation_paths)
    if arrays.get("schema_version") != "1":
        raise PayloadSchemaVersionError("simulation arrays", "1", arrays.get("schema_version"))

    bid_near_edges, bid_opp_edges, bid_profit, bid_sample_count = _grid_for_side(
        arrays,
        "bid",
        metric_key,
        settings,
    )
    ask_near_edges, ask_opp_edges, ask_profit, ask_sample_count = _grid_for_side(
        arrays,
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
            f"Bid Average {metric_label}",
            f"Ask Average {metric_label}",
            "Bid Sample Count",
            "Ask Sample Count",
        ),
    )

    figure.add_trace(
        _heatmap_trace(
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
        _heatmap_trace(
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

    figure.update_layout(
        title=f"{metric_label} Simulation",
        template="plotly_white",
        autosize=True,
        height=1500,
        margin={"l": 36, "r": 68, "t": 72, "b": 36},
    )
    return figure


def build_mid_profit_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_profit_view(locators, "mid_profit", render_options=render_options)


def build_micro_profit_view(
    locators: list[PlotDatasetLocator],
    render_options: PlotRenderOptions | None = None,
) -> go.Figure:
    return build_profit_view(locators, "micro_profit", render_options=render_options)

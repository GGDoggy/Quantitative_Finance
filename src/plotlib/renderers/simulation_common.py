from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


RESOLVED_ONLY = True


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

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.plotlib.options import PlotRenderOptions
from src.plotlib.renderers.trades_common import SIDE_COLORS, SIDE_LABELS, extract_trades
from src.plotlib.types import TradesPayloadV1


def build_trades_scatter_view(
    trade_frames_or_payloads: Sequence[TradesPayloadV1 | pd.DataFrame],
    render_options: PlotRenderOptions | None = None,
):
    del render_options
    trade_frame, product_id = extract_trades(trade_frames_or_payloads)

    figure = go.Figure()
    max_volume = max(trade_frame["Volume"].max(), 1e-9)

    for side_value, side_label in SIDE_LABELS.items():
        keeping = trade_frame.loc[trade_frame["Side"] == side_value]
        if keeping.empty:
            continue

        marker_size = 8 + 20 * np.sqrt(keeping["Volume"] / max_volume)
        figure.add_trace(
            go.Scattergl(
                x=keeping["Time"],
                y=keeping["Price"],
                mode="markers",
                name=side_label,
                marker={
                    "size": marker_size,
                    "color": SIDE_COLORS[side_value],
                    "opacity": 0.65,
                },
                text=[f"Volume: {value:.6f}" for value in keeping["Volume"]],
                hovertemplate="%{x}<br>Price=%{y}<br>%{text}<extra></extra>",
            )
        )

    figure.update_layout(
        title=f"Trades Scatter | {product_id}",
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        template="plotly_white",
        height=420,
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
    )
    return figure

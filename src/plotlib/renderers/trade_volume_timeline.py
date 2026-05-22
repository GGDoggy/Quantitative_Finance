from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src.plotlib.options import PlotRenderOptions
from src.plotlib.renderers.trades_common import SIDE_COLORS, SIDE_LABELS, extract_trades
from src.plotlib.types import TradesPayloadV1


def build_trade_volume_timeline_view(
    trade_frames_or_payloads: Sequence[TradesPayloadV1 | pd.DataFrame],
    render_options: PlotRenderOptions | None = None,
):
    del render_options
    trade_frame, product_id = extract_trades(trade_frames_or_payloads)

    figure = go.Figure()
    for side_value, side_label in SIDE_LABELS.items():
        keeping = trade_frame.loc[trade_frame["Side"] == side_value]
        if keeping.empty:
            continue

        figure.add_trace(
            go.Bar(
                x=keeping["Time"],
                y=keeping["Volume"],
                name=side_label,
                marker_color=SIDE_COLORS[side_value],
                opacity=0.8,
            )
        )

    figure.update_layout(
        title=f"Trade Volume Timeline | {product_id}",
        xaxis_title="Time",
        yaxis_title="Volume",
        template="plotly_white",
        barmode="overlay",
        height=360,
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
    )
    return figure

from __future__ import annotations

import plotly.graph_objects as go

from gui.data_catalog import PlotDatasetLocator

from gui.plots.trades_scatter import SIDE_COLORS, SIDE_LABELS, _extract_trades


def build_trade_volume_timeline_view(locators: list[PlotDatasetLocator]):
    trade_frame, product_id = _extract_trades(locators)

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

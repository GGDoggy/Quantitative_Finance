from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


SIDE_LABELS = {-1.0: "buy taker", 1.0: "sell taker"}
SIDE_COLORS = {-1.0: "#0FB353", 1.0: "#E23E1E"}


def _extract_trades(payloads: list[dict[str, object]]) -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    product_ids = set()

    for payload in payloads:
        product_ids.add(str(payload["product_id"]))
        required = {"trade_time", "trade_price", "trade_volume", "trade_side"}
        if not required.issubset(payload.keys()):
            continue

        trade_time = pd.to_datetime(np.asarray(payload["trade_time"]))
        frames.append(
            pd.DataFrame(
                {
                    "Time": trade_time,
                    "Price": np.asarray(payload["trade_price"], dtype=float),
                    "Volume": np.asarray(payload["trade_volume"], dtype=float),
                    "Side": np.asarray(payload["trade_side"], dtype=float),
                }
            )
        )

    if len(product_ids) != 1:
        raise ValueError("Trade views only support datasets from one product at a time.")

    if not frames:
        raise ValueError("Selected datasets do not contain trade data.")

    trade_frame = pd.concat(frames, ignore_index=True).sort_values("Time")
    return trade_frame, next(iter(product_ids))


def build_trades_scatter_view(payloads: list[dict[str, object]]):
    trade_frame, product_id = _extract_trades(payloads)

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

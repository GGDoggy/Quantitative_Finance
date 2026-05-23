from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .errors import PayloadSchemaVersionError, PreprocessedDataError
from .options import PlotRenderOptions
from .types import TradesPayloadV1, normalize_trades_payload_to_v1


TRADE_REQUIRED_KEYS = ("trade_time", "trade_price", "trade_volume", "trade_side")
SIDE_LABELS = {-1.0: "buy taker", 1.0: "sell taker"}
SIDE_COLORS = {-1.0: "#0FB353", 1.0: "#E23E1E"}


def load_trades_payload(
    path: Path | str,
    *,
    product_id: str,
    timestamp: str,
    time_step: float,
) -> TradesPayloadV1:
    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Trade dataset file does not exist: {dataset_path}")

    try:
        with np.load(dataset_path, allow_pickle=False) as data:
            missing_keys = [key for key in TRADE_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(
                    f"Trade dataset {dataset_path.name} is missing required key(s): "
                    f"{', '.join(missing_keys)}"
                )
            trade_time = pd.to_datetime(np.asarray(data["trade_time"]))
            payload = {
                "trade_time": trade_time.to_numpy(),
                "trade_price": np.asarray(data["trade_price"], dtype=float),
                "trade_volume": np.asarray(data["trade_volume"], dtype=float),
                "trade_side": np.asarray(data["trade_side"], dtype=float),
            }
    except KeyError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(
            f"Failed to load trade dataset {dataset_path.name}: {error}"
        ) from error

    return normalize_trades_payload_to_v1(
        {
            "product_id": product_id,
            "timestamp": timestamp,
            "time_step": time_step,
            **payload,
        }
    )


def load_trades_payloads(
    datasets: list[tuple[Path | str, str, str, float]],
) -> list[TradesPayloadV1]:
    return [
        load_trades_payload(
            path,
            product_id=product_id,
            timestamp=timestamp,
            time_step=time_step,
        )
        for path, product_id, timestamp, time_step in datasets
    ]


def extract_trades(
    items: Sequence[TradesPayloadV1 | pd.DataFrame],
) -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    product_ids = set()

    for item in items:
        if isinstance(item, pd.DataFrame):
            required_columns = {"Time", "Price", "Volume", "Side"}
            missing_columns = required_columns - set(item.columns)
            if missing_columns:
                raise KeyError(
                    f"Trade frame is missing required column(s): {', '.join(sorted(missing_columns))}"
                )
            trade_frame = item.copy()
        else:
            if item.get("schema_version") != "1":
                raise PayloadSchemaVersionError(
                    "trades payload", "1", item.get("schema_version")
                )
            trade_frame = pd.DataFrame(
                {
                    "Time": pd.to_datetime(item["trade_time"]),
                    "Price": np.asarray(item["trade_price"], dtype=float),
                    "Volume": np.asarray(item["trade_volume"], dtype=float),
                    "Side": np.asarray(item["trade_side"], dtype=float),
                }
            )
            trade_frame.attrs["product_id"] = item["product_id"]

        product_id = trade_frame.attrs.get("product_id")
        if product_id is None:
            raise ValueError("Loaded trade frames must include a product_id in DataFrame.attrs.")
        product_ids.add(str(product_id))
        frames.append(trade_frame)

    if not frames:
        raise ValueError("Selected datasets do not contain trade data.")
    if len(product_ids) != 1:
        raise ValueError("Trade views only support datasets from one product at a time.")

    trade_frame = pd.concat(frames, ignore_index=True).sort_values("Time")
    if trade_frame.empty:
        raise ValueError("Selected datasets do not contain trade rows.")
    return trade_frame, next(iter(product_ids))


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

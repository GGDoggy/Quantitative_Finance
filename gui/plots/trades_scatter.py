from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from gui.data_catalog import PlotDatasetLocator, PreprocessedDataError


SIDE_LABELS = {-1.0: "buy taker", 1.0: "sell taker"}
SIDE_COLORS = {-1.0: "#0FB353", 1.0: "#E23E1E"}
TRADE_REQUIRED_KEYS = ("trade_time", "trade_price", "trade_volume", "trade_side")


def _trade_path(locator: PlotDatasetLocator):
    return locator.preprocessed_dir / f"{locator.base_id}-orderbook_for_plot.npz"


def _load_trade_payload(locator: PlotDatasetLocator) -> pd.DataFrame:
    path = _trade_path(locator)
    if not path.is_file():
        raise FileNotFoundError(f"Trade dataset file does not exist: {path}")

    try:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [key for key in TRADE_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(
                    f"Trade dataset {path.name} is missing required key(s): {', '.join(missing_keys)}"
                )

            trade_time = pd.to_datetime(np.asarray(data["trade_time"]))
            trade_frame = pd.DataFrame(
                {
                    "Time": trade_time,
                    "Price": np.asarray(data["trade_price"], dtype=float),
                    "Volume": np.asarray(data["trade_volume"], dtype=float),
                    "Side": np.asarray(data["trade_side"], dtype=float),
                }
            )
    except KeyError:
        raise
    except (OSError, ValueError) as error:
        raise PreprocessedDataError(f"Failed to load trade dataset {path.name}: {error}") from error

    trade_frame.attrs["product_id"] = locator.product_id
    trade_frame.attrs["timestamp"] = locator.timestamp
    trade_frame.attrs["time_step"] = locator.time_step
    return trade_frame


def _extract_trades(items: Sequence[PlotDatasetLocator | pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    product_ids = set()

    for item in items:
        if isinstance(item, PlotDatasetLocator):
            trade_frame = _load_trade_payload(item)
        elif isinstance(item, pd.DataFrame):
            required_columns = {"Time", "Price", "Volume", "Side"}
            missing_columns = required_columns - set(item.columns)
            if missing_columns:
                raise KeyError(
                    f"Trade frame is missing required column(s): {', '.join(sorted(missing_columns))}"
                )
            trade_frame = item.copy()
        else:
            raise TypeError(f"Unsupported trade source: {type(item).__name__}")

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


def build_trades_scatter_view(locators: list[PlotDatasetLocator]):
    trade_frame, product_id = _extract_trades(locators)

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

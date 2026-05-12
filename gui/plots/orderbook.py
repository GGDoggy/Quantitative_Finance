from __future__ import annotations

from functools import partial

from bokeh.models import BasicTicker, ColorBar, LinearColorMapper
import holoviews as hv
from holoviews.operation.datashader import dynspread, rasterize, shade
import numpy as np
import pandas as pd


PLOT_WIDTH = 1200
PLOT_HEIGHT = 280
HEATMAP_CLIM = (-10, 10)
HEATMAP_LABEL = "Signed Depth"
HEATMAP_UNIT = "sign(volume) * log1p(|volume|)"
HEATMAP_COLOR_ANCHORS = [
    "#081D58",
    "#225EA8",
    "#1D91C0",
    "#F0F0F0",
    "#F46D43",
    "#D7301F",
    "#7F0000",
]


def interpolate_palette(colors: list[str], n_colors: int = 256) -> list[str]:
    anchor_rgb = np.array(
        [[int(color[index:index + 2], 16) for index in (1, 3, 5)] for color in colors],
        dtype=float,
    )
    anchor_positions = np.linspace(0, 1, len(anchor_rgb))
    sample_positions = np.linspace(0, 1, n_colors)
    channels = [
        np.interp(sample_positions, anchor_positions, anchor_rgb[:, channel])
        for channel in range(3)
    ]
    rgb = np.stack(channels, axis=1).round().astype(int)
    return [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in rgb]


HEATMAP_COLORS = interpolate_palette(HEATMAP_COLOR_ANCHORS)


def add_heatmap_colorbar(plot, _):
    if getattr(plot.state, "_orderbook_colorbar_added", False):
        return

    color_mapper = LinearColorMapper(palette=HEATMAP_COLORS, low=HEATMAP_CLIM[0], high=HEATMAP_CLIM[1])
    color_bar = ColorBar(
        color_mapper=color_mapper,
        ticker=BasicTicker(desired_num_ticks=7),
        title=f"{HEATMAP_LABEL} ({HEATMAP_UNIT})",
        label_standoff=8,
    )
    plot.state.add_layout(color_bar, "right")
    plot.state._orderbook_colorbar_added = True


def get_canvas_full(x_range, y_range, time_axis, price_axis, volume, default_range):
    if x_range is None or x_range[0] is None or y_range is None or y_range[0] is None:
        x_range, y_range = default_range

    time_ns = time_axis.view("int64")
    start_ns = pd.Timestamp(x_range[0]).value
    end_ns = pd.Timestamp(x_range[1]).value
    start_price, end_price = y_range

    x0 = max(0, np.searchsorted(time_ns, start_ns, side="left"))
    x1 = min(len(time_axis), np.searchsorted(time_ns, end_ns, side="right"))
    y0 = max(0, np.searchsorted(price_axis, start_price, side="left"))
    y1 = min(len(price_axis), np.searchsorted(price_axis, end_price, side="right"))

    if x0 == x1:
        x1 = min(len(time_axis), x0 + 1)
    if y0 == y1:
        y1 = min(len(price_axis), y0 + 1)

    return hv.QuadMesh(
        (
            time_axis[x0:x1],
            price_axis[y0:y1],
            volume[y0:y1, x0:x1],
        ),
        kdims=["Time", "Price"],
        vdims=["Volume"],
    )


def get_price_line(x_range, y_range, raw: pd.DataFrame, name: str, color: str, default_range):
    if x_range is None or x_range[0] is None:
        x_range = default_range

    start_time = pd.Timestamp(x_range[0])
    end_time = pd.Timestamp(x_range[1])
    keeping = raw.loc[raw["Time"].between(start_time, end_time)]
    value_col = next(column for column in raw.columns if column != "Time")

    if keeping.empty:
        return hv.Curve([], kdims=["Time"], vdims=[value_col], label=name).opts(color=color, line_width=2)

    return hv.Curve(keeping, kdims=["Time"], vdims=[value_col], label=name).opts(color=color, line_width=2)


def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
    price_axis = np.asarray(payload["price_axis"], dtype=float)
    time_axis = pd.to_datetime(np.asarray(payload["time_axis"]))
    raw_volume = np.asarray(payload["data"], dtype=float).T
    signed_volume = np.sign(raw_volume) * np.log1p(np.abs(raw_volume))
    bid = np.asarray(payload["bid"], dtype=float)
    ask = np.asarray(payload["ask"], dtype=float)
    if "mid" in payload:
        mid = np.asarray(payload["mid"], dtype=float)
    else:
        mid = 0.5 * (bid + ask)

    return {
        "product_id": payload["product_id"],
        "price_axis": price_axis,
        "time_axis": time_axis,
        "volume": signed_volume,
        "bid": bid,
        "ask": ask,
        "mid": mid,
    }


def _merge_payloads(payloads: list[dict[str, object]]) -> dict[str, object]:
    normalized = [_normalize_payload(payload) for payload in payloads]
    product_ids = {item["product_id"] for item in normalized}
    if len(product_ids) != 1:
        raise ValueError("Orderbook view only supports datasets from one product at a time.")

    common_price_axis = np.unique(
        np.concatenate([np.asarray(item["price_axis"], dtype=float) for item in normalized])
    )

    combined_times: list[pd.Timestamp] = []
    combined_bid: list[float] = []
    combined_ask: list[float] = []
    combined_mid: list[float] = []
    aligned_chunks: list[np.ndarray] = []

    previous_end: pd.Timestamp | None = None
    for item in sorted(normalized, key=lambda value: value["time_axis"][0]):
        time_axis = pd.DatetimeIndex(item["time_axis"])
        volume = np.asarray(item["volume"], dtype=float)
        aligned_volume = np.zeros((len(common_price_axis), volume.shape[1]), dtype=float)
        source_index = np.searchsorted(common_price_axis, item["price_axis"])
        aligned_volume[source_index, :] = volume

        if previous_end is not None and len(time_axis) > 0 and time_axis[0] > previous_end:
            separator_time = previous_end + (time_axis[0] - previous_end) / 2
            combined_times.append(separator_time)
            combined_bid.append(np.nan)
            combined_ask.append(np.nan)
            combined_mid.append(np.nan)
            aligned_chunks.append(np.full((len(common_price_axis), 1), np.nan))

        combined_times.extend(list(time_axis))
        combined_bid.extend(np.asarray(item["bid"], dtype=float).tolist())
        combined_ask.extend(np.asarray(item["ask"], dtype=float).tolist())
        combined_mid.extend(np.asarray(item["mid"], dtype=float).tolist())
        aligned_chunks.append(aligned_volume)
        previous_end = time_axis[-1]

    if not aligned_chunks:
        raise ValueError("No orderbook payloads available.")

    return {
        "product_id": next(iter(product_ids)),
        "price_axis": common_price_axis,
        "time_axis": pd.to_datetime(combined_times),
        "volume": np.concatenate(aligned_chunks, axis=1),
        "bid": np.array(combined_bid, dtype=float),
        "ask": np.array(combined_ask, dtype=float),
        "mid": np.array(combined_mid, dtype=float),
    }


def build_orderbook_view(payloads: list[dict[str, object]]):
    merged = _merge_payloads(payloads)
    raw_time_axis = merged["time_axis"]
    raw_price_axis = merged["price_axis"]
    raw_volume = merged["volume"]
    raw_bid = pd.DataFrame({"Time": raw_time_axis, "bid": merged["bid"]})
    raw_ask = pd.DataFrame({"Time": raw_time_axis, "ask": merged["ask"]})
    raw_mid = pd.DataFrame({"Time": raw_time_axis, "mid": merged["mid"]})

    valid_mid = raw_mid["mid"].dropna()
    if raw_bid.empty or valid_mid.empty:
        raise ValueError("No orderbook samples are available for the selected datasets.")

    end_time = raw_bid["Time"].dropna().iat[-1]
    start_time = raw_bid["Time"].dropna().iat[0]
    last_mid = valid_mid.iat[-1]
    start_price = last_mid - 2.5
    end_price = last_mid + 2.5

    default_range = ((start_time, end_time), (start_price, end_price))
    range_stream = hv.streams.RangeXY()
    get_canvas = partial(
        get_canvas_full,
        time_axis=raw_time_axis,
        price_axis=raw_price_axis,
        volume=raw_volume,
        default_range=default_range,
    )

    heatmap = hv.DynamicMap(get_canvas, streams=[range_stream])
    range_stream.source = heatmap

    rasterized_heatmap = rasterize(heatmap, width=PLOT_WIDTH, height=PLOT_HEIGHT, dynamic=True)
    shaded_heatmap = shade(rasterized_heatmap, cmap=HEATMAP_COLORS, clims=HEATMAP_CLIM, cnorm="linear")
    spread_heatmap = dynspread(shaded_heatmap, threshold=0.8, max_px=10)

    get_bid = partial(get_price_line, raw=raw_bid, name="bid", color="#0FB353", default_range=(start_time, end_time))
    get_ask = partial(get_price_line, raw=raw_ask, name="ask", color="#E23E1E", default_range=(start_time, end_time))
    get_mid = partial(get_price_line, raw=raw_mid, name="mid", color="#3979B9", default_range=(start_time, end_time))

    bid_line = hv.DynamicMap(get_bid, streams=[range_stream])
    ask_line = hv.DynamicMap(get_ask, streams=[range_stream])
    mid_line = hv.DynamicMap(get_mid, streams=[range_stream])

    return (spread_heatmap * bid_line * ask_line * mid_line).opts(
        width=1400,
        height=720,
        xlim=(start_time, end_time),
        ylim=(start_price, end_price),
        xlabel="Time",
        ylabel="Price (USD)",
        bgcolor="#081421",
        title=f"Orderbook | {merged['product_id']}",
        hooks=[add_heatmap_colorbar],
    )

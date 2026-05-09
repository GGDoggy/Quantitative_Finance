from os import walk
from functools import partial

import holoviews as hv
import numpy as np
import pandas as pd
import panel as pn
from bokeh.models import BasicTicker, ColorBar, LinearColorMapper
from holoviews.operation.datashader import dynspread, rasterize, shade


def search_data(path: str):
    for _, _, files in walk(path):
        filelist = files
        break
    else:
        return [], []

    file_list = []
    ids = set()
    for file in filelist:
        split = file.split("-")
        product_id = "-".join(split[:-3])
        time_step = float(split[-2])
        file_list.append((product_id, time_step, file))
        ids.add(product_id)

    return file_list, list(ids)


def load_data(path: str):
    data = np.load(path)
    price_axis = data["price_axis"]
    time_axis = pd.to_datetime(data["time_axis"])
    volume = data["data"].T
    bid = data["bid"]
    ask = data["ask"]
    signed_log_volume = np.sign(volume) * np.log1p(np.abs(volume))

    return price_axis, time_axis, signed_log_volume, bid, ask


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

    sliced_time = time_axis[x0:x1]
    sliced_price = price_axis[y0:y1]
    sliced_volume = volume[y0:y1, x0:x1]

    return hv.QuadMesh((sliced_time, sliced_price, sliced_volume), kdims=["Time", "Price"], vdims=["Volume"])


def get_price_line(x_range, y_range, raw, name, color, default_range):
    if x_range is None or x_range[0] is None:
        x_range = default_range

    start_time = pd.Timestamp(x_range[0])
    end_time = pd.Timestamp(x_range[1])
    mask = raw["Time"].between(start_time, end_time)
    keeping = raw.loc[mask]
    value_col = next(col for col in raw.columns if col != "Time")

    if keeping.empty:
        return hv.Curve([], kdims=["Time"], vdims=[value_col], label=name).opts(color=color, line_width=2)

    return hv.Curve(keeping, kdims=["Time"], vdims=[value_col], label=name).opts(color=color, line_width=2)


time_step = 0.01
path = "data/preprocessed/"
id = "ETH-USD"
init_price_interval = 5
init_time_interval = 30
plot_width = 1000
plot_height = 200
heatmap_clim = (-10, 10)
heatmap_label = "Signed Depth"
heatmap_unit = "sign(volume) * log1p(|volume|)"
heatmap_color_anchors = [
    "#081D58",
    "#225EA8",
    "#1D91C0",
    "#F0F0F0",
    "#F46D43",
    "#D7301F",
    "#7F0000",
]


def interpolate_palette(colors, n_colors=256):
    anchor_rgb = np.array(
        [[int(color[i:i + 2], 16) for i in (1, 3, 5)] for color in colors],
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


heatmap_colors = interpolate_palette(heatmap_color_anchors)


def add_heatmap_colorbar(plot, _):
    if getattr(plot.state, "_orderbook_colorbar_added", False):
        return

    color_mapper = LinearColorMapper(palette=heatmap_colors, low=heatmap_clim[0], high=heatmap_clim[1])
    color_bar = ColorBar(
        color_mapper=color_mapper,
        ticker=BasicTicker(desired_num_ticks=7),
        title=f"{heatmap_label} ({heatmap_unit})",
        label_standoff=8,
    )
    plot.state.add_layout(color_bar, "right")
    plot.state._orderbook_colorbar_added = True


def build_layout():
    raw_bid = pd.DataFrame({"Time": [], "bid": []})
    raw_ask = pd.DataFrame({"Time": [], "ask": []})
    raw_mid = pd.DataFrame({"Time": [], "mid": []})
    raw_time_axis = None
    raw_price_axis = None
    raw_volume = None

    file_list, _ = search_data(path)

    for file in file_list:
        if file[0] != id:
            continue

        price_axis, time_axis, volume, bid, ask = load_data(path + file[2])
        mid = 0.5 * (bid + ask)

        raw_price_axis = price_axis
        raw_time_axis = time_axis
        raw_volume = volume
        raw_bid = pd.concat([raw_bid, pd.DataFrame({"Time": time_axis, "bid": bid})], ignore_index=True)
        raw_ask = pd.concat([raw_ask, pd.DataFrame({"Time": time_axis, "ask": ask})], ignore_index=True)
        raw_mid = pd.concat([raw_mid, pd.DataFrame({"Time": time_axis, "mid": mid})], ignore_index=True)

        break

    if raw_bid.empty:
        raise FileNotFoundError(f"No preprocessed data found for product id '{id}' in '{path}'.")

    raw_bid.sort_values("Time", inplace=True)
    raw_ask.sort_values("Time", inplace=True)
    raw_mid.sort_values("Time", inplace=True)

    end_time = raw_bid["Time"].iat[-1]
    start_time = end_time - pd.Timedelta(seconds=init_time_interval)
    end_mid = raw_mid["mid"].iat[-1]
    start_price = end_mid - init_price_interval / 2
    end_price = end_mid + init_price_interval / 2

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

    rasterized_heatmap = rasterize(heatmap, width=plot_width, height=plot_height, dynamic=True)
    shaded_heatmap = shade(rasterized_heatmap, cmap=heatmap_colors, clims=heatmap_clim, cnorm="linear")
    spread_heatmap = dynspread(shaded_heatmap, threshold=0.8, max_px=10)

    get_bid = partial(get_price_line, raw=raw_bid, name="bid", color="#0FB353", default_range=(start_time, end_time))
    get_ask = partial(get_price_line, raw=raw_ask, name="ask", color="#E23E1E", default_range=(start_time, end_time))
    get_mid = partial(get_price_line, raw=raw_mid, name="mid", color="#3979B9", default_range=(start_time, end_time))

    bid_line = hv.DynamicMap(get_bid, streams=[range_stream])
    ask_line = hv.DynamicMap(get_ask, streams=[range_stream])
    mid_line = hv.DynamicMap(get_mid, streams=[range_stream])

    return (spread_heatmap * bid_line * ask_line * mid_line).opts(
        width=2000,
        height=800,
        xlim=(start_time, end_time),
        ylim=(start_price, end_price),
        xlabel="Time",
        ylabel="Price (USD)",
        bgcolor="#081421",
        hooks=[add_heatmap_colorbar],
    )


def main():
    hv.extension("bokeh")
    layout = build_layout()
    pn.serve(layout, title="Orderbook Viewer")


if __name__ == "__main__":
    main()

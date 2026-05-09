from os import walk
import numpy as np
import datashader as ds
import holoviews as hv
import pandas as pd
import panel as pn
import matplotlib.colors as mcolors
from holoviews.operation.datashader import dynspread
from functools import partial


def search_data(path: str):
    for a, b, c in walk(path):
        filelist = c
        break
    
    file_list = []
    ids = set()
    for file in filelist:
        split = file.split("-")
        id = "-".join(split[:-3])
        time_step = float(split[-2])
        file_list.append((id, time_step, file))
        ids.add(id)

    return file_list, list(ids)

def load_data(path: str):
    data = np.load(path)
    price_axis = data["price_axis"]
    time_axis = data["time_axis"].astype(np.int64)
    volume = data["data"].T
    bid = data["bid"]
    ask = data["ask"]
    T, P = np.meshgrid(time_axis, price_axis)
    volume = pd.DataFrame({"Time": T.flatten(), "Price": P.flatten(), "sumVolume": np.abs(volume).flatten(), "diffVolume": volume.flatten()})

    return price_axis, time_axis, volume, bid, ask

def compute_pixel(dataset):
    sumVol = dataset.data.sumVol
    diffVol = dataset.data.diffVol

    ask = (sumVol + diffVol) * 0.5
    bid = (sumVol - diffVol) * 0.5
    volume = np.where(ask > bid, np.log1p(ask), -np.log1p(bid))

    return hv.Image((dataset.data.Time.astype("datetime64[ns]"), dataset.data.Price, volume))

def get_canvas_full(x_range, y_range, raw_volume, total_start_time, default_range):
    if x_range is None or y_range is None:
        x_range = default_range[0]
        y_range = default_range[1]
    start_time = pd.to_datetime(x_range[0]).timestamp() - total_start_time
    end_time = pd.to_datetime(x_range[1]).timestamp() - total_start_time
    canvas = ds.Canvas(plot_width=plot_width, plot_height=plot_height, y_range=y_range, x_range=(start_time, end_time))
    agg_sum = canvas.points(raw_volume, "Time", "Price", ds.reductions.sum("sumVolume"))
    agg_diff = canvas.points(raw_volume, "Time", "Price", ds.reductions.sum("diffVolume"))
    plot_x = pd.to_datetime(agg_sum["Time"] + total_start_time, unit="s")
    plot_y = agg_sum["Price"]
    agg_sum = np.nan_to_num(agg_sum, nan=0.0)
    agg_diff = np.nan_to_num(agg_diff, nan=0.0)
    ask_volume = (agg_sum + agg_diff) * 0.5
    bid_volume = (agg_sum - agg_diff) * 0.5
    plot_z = np.where(ask_volume > bid_volume, np.log1p(ask_volume), -np.log1p(bid_volume))
    plot_z.reshape((len(plot_x), len(plot_y)))

    return hv.Image((plot_x, plot_y, plot_z))

def get_price_line(x_range, y_range, raw, name, color, default_range):
    if x_range is None or (x_range[0] is None):
        x_range = default_range
    
    try:
        s_val = x_range[0]
        e_val = x_range[1]
        
        start_ts = pd.to_datetime(s_val).timestamp()
        end_ts = pd.to_datetime(e_val).timestamp()
        
        time_array = raw["Time"].values.astype(float)
        mask = (time_array >= start_ts) & (time_array <= end_ts)
        keeping = raw.loc[mask]
        
        value_col = [c for c in raw.columns if c != "Time"][0]
        
        return hv.Curve(keeping, kdims=["Time"], vdims=[value_col], name=name).opts(
            color=color, line_width=2
        )
    except Exception as e:
        print(f"Error in get_price_line: {e}")
        return hv.Curve([], kdims=["Time"], vdims=["Value"], name=name)
    


time_step = 0.01
path = "data/preprocessed/"
id = "ETH-USD"
init_price_interval = 5
init_time_interval = 30
plot_width = 1000
plot_height = 200


raw_volume = pd.DataFrame({"Time": [], "Price": [], "sumVolume": [], "diffVolume": []})
raw_bid = pd.DataFrame({"Time": [], "bid": []})
raw_ask = pd.DataFrame({"Time": [], "ask": []})
raw_mid = pd.DataFrame({"Time": [], "mid": []})

file_list, ids = search_data(path)

# Load data
for file in file_list:
    if file[0] != id:
        continue
        
    price_axis, time_axis, volume, bid, ask = load_data(path + file[2])
    mid = 0.5 * (bid + ask)

    raw_volume = pd.concat([raw_volume, volume])
    raw_bid = pd.concat([raw_bid, pd.DataFrame({"Time": time_axis, "bid": bid})])
    raw_ask = pd.concat([raw_ask, pd.DataFrame({"Time": time_axis, "ask": ask})])
    raw_mid = pd.concat([raw_mid, pd.DataFrame({"Time": time_axis, "mid": mid})])


    break



# Sort data by time
raw_bid.sort_values("Time", inplace=True)
raw_ask.sort_values("Time", inplace=True)
raw_mid.sort_values("Time", inplace=True)

# Calculate init axis range
total_start_time = raw_bid["Time"][0]
end_time = raw_bid["Time"].iat[-1]
start_time = int(end_time - init_time_interval * 1e9)
end_mid = raw_mid["mid"].iat[-1]
start_price = end_mid - init_price_interval / 2
end_price = end_mid + init_price_interval / 2
start_time = pd.to_datetime(start_time, unit="ns")
end_time = pd.to_datetime(end_time, unit="ns")

# Dynamic plot
raw_volume["Time"] -= total_start_time
raw_volume["Time"] /= 1e9
range_stream = hv.streams.RangeXY()
get_canvas = partial(get_canvas_full, raw_volume=raw_volume, total_start_time=total_start_time/1e9, default_range=((start_time, end_time), (start_price, end_price)))
plot = hv.DynamicMap(get_canvas, streams=[range_stream])
plot = dynspread(plot, threshold=0.8, max_px=10)
range_stream.source = plot

# Prepare price line data
# raw_bid["Time"] /= 1e9
# raw_ask["Time"] /= 1e9
# raw_mid["Time"] /= 1e9
# get_bid = partial(get_price_line, raw=raw_bid, name="bid", color='#00FF00', default_range=(start_time, end_time))
# get_ask = partial(get_price_line, raw=raw_ask, name="ask", color='#FF0000', default_range=(start_time, end_time))
# get_mid = partial(get_price_line, raw=raw_mid, name="mid", color='#00949B', default_range=(start_time, end_time))

# Plot
hv.extension("bokeh")
# bid_line = hv.DynamicMap(get_bid, streams=[range_stream])
# ask_line = hv.DynamicMap(get_ask, streams=[range_stream])
# mid_line = hv.DynamicMap(get_mid, streams=[range_stream])

# Custom color map
colors = ["#0058FF", "#E7E7E7", "#FF6F06"]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("black_rainbow", colors, N=256)


# agg = rasterize(
#     hv.Points(raw_volume, kdims=['Time', 'Price'], vdims=['sumVolume', 'diffVolume']),
#     aggregator=ds.summary(sumVol=ds.sum('sumVolume'), diffVol=ds.sum('diffVolume'))
# )
# dynamic_img = agg.apply(compute_pixel)
# colors = ["#0058FF", "#E7E7E7", "#FF6F06"]
# custom_cmap = mcolors.LinearSegmentedColormap.from_list("black_rainbow", colors, N=256)
# final_plot = dynamic_img.opts(
#     width=plot_width, 
#     height=plot_height,
#     colorbar=True,
#     cmap=custom_cmap,
#     clim=(-10, 10)
# )


# Layout
# max_val = np.max(np.abs(plot_z))
plot.opts(width=2000, height=800, colorbar=True, cmap=custom_cmap, clim=(-10, 10))
# layout = pn.Column(plot)
layout = (plot).opts(xlim=(start_time, end_time), ylim=(start_price, end_price))
pn.serve(layout, show=True, title="Orderbook Viewer")
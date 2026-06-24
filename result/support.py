from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import colors


ORDERBOOK_FIELDS = (
    "time_axis",
    "bid_price",
    "bid_size",
    "ask_price",
    "ask_size",
    "bid",
    "ask",
    "mid",
)
TRADE_FIELDS = (
    "trade_time",
    "trade_price",
    "trade_volume",
    "trade_side",
)
FIELD_MAP = {
    "orderbook": ORDERBOOK_FIELDS,
    "trade": TRADE_FIELDS,
}
WINDOW_METADATA_KEYS = {
    "orderbook": "orderbook_window_seconds_available",
    "trade": "trade_window_seconds_available",
}
WINDOW_LATEST_KEYS = {
    "orderbook": "orderbook_window_seconds_latest",
    "trade": "trade_window_seconds_latest",
}
PRIMARY_TIME_FIELD = {
    "orderbook": "time_axis",
    "trade": "trade_time",
}


def load_npz(path):
    with np.load(path) as file:
        return {key: file[key] for key in file.files}


def _ensure_supported_kind(kind: str) -> None:
    if kind not in FIELD_MAP:
        raise ValueError(f"Unsupported preprocess kind: {kind!r}. Expected one of {sorted(FIELD_MAP)}.")


def _coerce_window_list(value) -> list[int]:
    arr = np.atleast_1d(value)
    windows = []
    for item in arr.tolist():
        if item is not None:
            windows.append(int(item))
    return sorted(set(windows))


def list_available_windows(npz_data, kind):
    _ensure_supported_kind(kind)
    metadata_key = WINDOW_METADATA_KEYS[kind]
    latest_key = WINDOW_LATEST_KEYS[kind]
    if metadata_key in npz_data:
        return _coerce_window_list(npz_data[metadata_key])
    if latest_key in npz_data:
        return _coerce_window_list(npz_data[latest_key])
    raise KeyError(f"Missing window metadata {metadata_key!r} for preprocess kind {kind!r}.")


def window_key(base_name, window_seconds):
    return f"{base_name}__w{int(window_seconds)}"


def load_window_payload(npz_data, kind, window_seconds):
    _ensure_supported_kind(kind)
    payload = {}
    missing_keys = []
    for field_name in FIELD_MAP[kind]:
        key = window_key(field_name, window_seconds)
        if key not in npz_data:
            missing_keys.append(key)
            continue
        payload[field_name] = npz_data[key]
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise KeyError(
            f"Preprocess kind {kind!r} is missing required keys for w{window_seconds}: {missing}."
        )
    return payload


def get_aggregated_window_data(path, kind):
    _ensure_supported_kind(kind)
    root = Path(path)
    pattern = f"preprocess-{kind}-*.npz"
    targets = sorted(root.glob(pattern))
    if not targets:
        raise FileNotFoundError(f"No preprocess artifacts matching {pattern!r} were found under {root}.")

    aggregated = {}
    for target in targets:
        npz_data = load_npz(target)
        for window_seconds in list_available_windows(npz_data, kind):
            payload = load_window_payload(npz_data, kind, window_seconds)
            bucket = aggregated.setdefault(
                window_seconds,
                {field_name: [] for field_name in FIELD_MAP[kind]},
            )
            for field_name, values in payload.items():
                bucket[field_name].append(values)

    return {
        window_seconds: {
            field_name: np.concatenate(values)
            for field_name, values in field_buckets.items()
        }
        for window_seconds, field_buckets in aggregated.items()
    }


def ensure_windows(window_payloads, required_windows, kind):
    _ensure_supported_kind(kind)
    missing_windows = [int(window) for window in required_windows if int(window) not in window_payloads]
    if missing_windows:
        missing = ", ".join(f"w{window}" for window in missing_windows)
        raise ValueError(
            f"Preprocess kind {kind!r} is missing required windows: {missing}. "
            f"Available windows: {sorted(window_payloads)}."
        )


def ensure_nonempty_windows(window_payloads, required_windows, kind):
    _ensure_supported_kind(kind)
    ensure_windows(window_payloads, required_windows, kind)
    primary_field = PRIMARY_TIME_FIELD[kind]
    empty_windows = [
        int(window)
        for window in required_windows
        if len(np.asarray(window_payloads[int(window)][primary_field])) == 0
    ]
    if empty_windows:
        missing = ", ".join(f"w{window}" for window in empty_windows)
        raise ValueError(
            f"Preprocess kind {kind!r} has empty payloads for required windows: {missing}. "
            "Prepare non-empty preprocess artifacts before running this analysis."
        )


def load_and_validate_data(
    preprocess_path,
    orderbook_windows,
    trade_windows,
    base_window_for_correlation,
):
    orderbook_by_window = get_aggregated_window_data(preprocess_path, "orderbook")
    trade_by_window = get_aggregated_window_data(preprocess_path, "trade")

    ensure_nonempty_windows(orderbook_by_window, orderbook_windows, "orderbook")
    ensure_nonempty_windows(trade_by_window, trade_windows, "trade")

    if base_window_for_correlation not in orderbook_by_window:
        raise ValueError(
            f"Correlation base window w{base_window_for_correlation} is missing from orderbook preprocess artifacts."
        )
    if base_window_for_correlation not in trade_by_window:
        raise ValueError(
            f"Correlation base window w{base_window_for_correlation} is missing from trade preprocess artifacts."
        )

    print("Orderbook windows:", sorted(orderbook_by_window))
    print("Trade windows:", sorted(trade_by_window))
    return orderbook_by_window, trade_by_window


def _calc_fix_window_feature(time, arr, time_window, feature_func, extra=None):
    time = pd.to_datetime(np.asarray(time))
    arr = np.asarray(arr)
    if len(time) != len(arr):
        raise ValueError("Length of time array and target array must match.")

    i_front = 0
    i_back = 0
    end = len(time)
    accept_time = time_window + pd.Timedelta(seconds=1)
    feature_arr = []
    extra_info = extra(time, arr, time_window) if extra is not None else None
    while i_front < end and i_back < end:
        time_diff = time[i_front] - time[i_back]
        if time_diff < time_window:
            i_front += 1
            continue
        if time_diff < accept_time:
            feature_arr.append(feature_func(i_front, i_back, time, arr, extra_info))
            i_back += 1
            continue
        i_back += 1

    if not feature_arr:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)

    time_values, feature_values = zip(*feature_arr)
    return np.asarray(time_values), np.asarray(feature_values, dtype=float)


def _get_price_change_tup(i_front, i_back, time, price, extra_info):
    return time[i_back], price[i_front] - price[i_back]


def calc_price_change_series(time, price, horizon_seconds):
    time_window = pd.Timedelta(seconds=int(horizon_seconds))
    return _calc_fix_window_feature(time, price, time_window, _get_price_change_tup)


def _get_average_tup(i_front, i_back, time, price_change, extra_info):
    return time[i_front], np.mean(price_change[i_back : i_front + 1])


def calc_price_change_average_series(time, price_change, average_window_seconds):
    time_window = pd.Timedelta(seconds=int(average_window_seconds))
    return _calc_fix_window_feature(time, price_change, time_window, _get_average_tup)


def _variance_extra(time, arr, time_window):
    return arr ** 2


def _get_variance_tup(i_front, i_back, time, profit, arr_square):
    return time[i_front], np.mean(arr_square[i_back : i_front + 1])


def calc_variance_series(time, profit, variance_window_seconds):
    time_window = pd.Timedelta(seconds=int(variance_window_seconds))
    return _calc_fix_window_feature(time, profit, time_window, _get_variance_tup, _variance_extra)


def spread_from_orderbook_window(orderbook_window):
    return np.asarray(orderbook_window["ask"], dtype=float) - np.asarray(orderbook_window["bid"], dtype=float)


def trade_volume_per_second(trade_window, window_seconds):
    return np.asarray(trade_window["trade_volume"], dtype=float) / float(window_seconds)


def mean_2d_binned(x, y, value, bins, fig_range):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    value = np.asarray(value, dtype=float)
    value_sum, x_edge, y_edge = np.histogram2d(
        x,
        y,
        bins=bins,
        range=(fig_range, fig_range),
        weights=value,
    )
    value_count, _, _ = np.histogram2d(
        x,
        y,
        bins=bins,
        range=(fig_range, fig_range),
    )
    mean_value = np.full_like(value_sum, np.nan, dtype=float)
    np.divide(value_sum, value_count, out=mean_value, where=value_count > 0)
    return mean_value, x_edge, y_edge


def aggregate_by_time(target_time, target_values, agg="sum"):
    target_time = pd.to_datetime(np.asarray(target_time))
    target_values = np.asarray(target_values, dtype=float)
    if len(target_time) != len(target_values):
        raise ValueError("Time and value arrays must have the same length.")

    series = pd.Series(target_values, index=target_time)
    if series.index.has_duplicates:
        grouped = series.groupby(level=0)
        if agg == "sum":
            series = grouped.sum()
        elif agg == "mean":
            series = grouped.mean()
        elif agg == "last":
            series = grouped.last()
        elif agg == "first":
            series = grouped.first()
        else:
            raise ValueError(f"Unsupported aggregation mode: {agg!r}.")
    return series.sort_index()


def align_on_time(reference_time, target_time, target_values, agg="sum"):
    reference_time = pd.to_datetime(np.asarray(reference_time))
    lookup = aggregate_by_time(target_time, target_values, agg=agg)
    aligned = lookup.reindex(reference_time)
    return aligned.to_numpy(dtype=float)


def top_level_sizes(orderbook_window):
    return (
        np.asarray(orderbook_window["bid_size"], dtype=float)[:, 0],
        np.asarray(orderbook_window["ask_size"], dtype=float)[:, 0],
    )


def depth_sizes(orderbook_window, depth):
    bid_size = np.asarray(orderbook_window["bid_size"], dtype=float)
    ask_size = np.asarray(orderbook_window["ask_size"], dtype=float)
    return bid_size[:, :depth].sum(axis=1), ask_size[:, :depth].sum(axis=1)


def build_symmetric_two_slope_norm(abs_limit):
    abs_limit = float(abs_limit)
    if not np.isfinite(abs_limit) or abs_limit <= 0:
        raise ValueError("PRICE_CHANGE_HEATMAP_ABS_LIMIT must be a positive finite number.")
    return colors.TwoSlopeNorm(vmin=-abs_limit, vcenter=0.0, vmax=abs_limit)


def build_normal_fit_curve(values, points=400):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return None, None, None, None

    mean = float(values.mean())
    std = float(values.std(ddof=0))
    if not np.isfinite(mean) or not np.isfinite(std) or std <= 0:
        return None, None, mean, std

    x_min = float(values.min())
    x_max = float(values.max())
    if not np.isfinite(x_min) or not np.isfinite(x_max):
        return None, None, mean, std
    if x_min == x_max:
        x_min = mean - 4.0 * std
        x_max = mean + 4.0 * std
    x_grid = np.linspace(x_min, x_max, points)
    pdf = np.exp(-0.5 * ((x_grid - mean) / std) ** 2) / (std * np.sqrt(2.0 * np.pi))
    return x_grid, pdf, mean, std


def filter_spread_normal_fit_samples(spread_tick, x_min, x_max, fit_label="spread normal fit"):
    spread_tick = np.asarray(spread_tick, dtype=float)
    spread_tick = spread_tick[np.isfinite(spread_tick)]
    if spread_tick.size == 0:
        raise ValueError(f"{fit_label}: spread_tick has no finite samples.")

    x_min = float(x_min)
    x_max = float(x_max)
    if not np.isfinite(x_min) or not np.isfinite(x_max):
        raise ValueError(f"{fit_label}: x_min and x_max must be finite.")
    if x_min > x_max:
        raise ValueError(f"{fit_label}: x_min must be smaller than or equal to x_max.")

    mask = (spread_tick >= x_min) & (spread_tick <= x_max)
    filtered_samples = spread_tick[mask]
    if filtered_samples.size < 2:
        raise ValueError(
            f"{fit_label}: tick x-range [{x_min}, {x_max}] leaves fewer than 2 finite samples."
        )
    return filtered_samples


def build_plot_curve_mask(x_values, y_values, require_positive_x=False):
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x_values) & np.isfinite(y_values) & (y_values > 0)
    if require_positive_x:
        mask = mask & (x_values > 0)
    return mask


def resolve_histogram_bin_edges(values, bins, use_log_bins, fit_label):
    if isinstance(bins, (int, np.integer)):
        bin_count = int(bins)
        if bin_count < 2:
            raise ValueError(f"{fit_label}: histogram bin count must be at least 2, got {bin_count}.")
        if use_log_bins:
            positive_values = values[values > 0]
            if positive_values.size == 0:
                raise ValueError(f"{fit_label}: log histogram requires at least one positive value.")
            positive_min = float(positive_values.min())
            positive_max = float(positive_values.max())
            if positive_max > positive_min:
                return np.logspace(np.log10(positive_min), np.log10(positive_max), bin_count + 1)
            return np.array([positive_min, positive_min * 1.01], dtype=float)
        return bin_count

    bin_edges = np.asarray(bins, dtype=float)
    if bin_edges.ndim != 1 or bin_edges.size < 2:
        raise ValueError(f"{fit_label}: histogram bin edges must be a 1D array with at least 2 values.")
    if not np.all(np.isfinite(bin_edges)):
        raise ValueError(f"{fit_label}: histogram bin edges must all be finite.")
    if np.any(np.diff(bin_edges) <= 0):
        raise ValueError(f"{fit_label}: histogram bin edges must be strictly increasing.")
    if use_log_bins and np.any(bin_edges <= 0):
        raise ValueError(f"{fit_label}: log histogram bin edges must be strictly positive.")
    return bin_edges


def build_density_histogram(raw_values, bins, use_log_bins=False, fit_label="histogram"):
    values = np.asarray(raw_values, dtype=float)
    values = values[np.isfinite(values)]
    if use_log_bins:
        values = values[values > 0]
    if values.size == 0:
        raise ValueError(f"{fit_label}: no finite values available to build the histogram.")

    bin_edges = resolve_histogram_bin_edges(values, bins=bins, use_log_bins=use_log_bins, fit_label=fit_label)
    hist_density, bin_edges = np.histogram(values, bins=bin_edges, density=True)
    hist_density = np.asarray(hist_density, dtype=float)
    bin_edges = np.asarray(bin_edges, dtype=float)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    return {
        "values": values,
        "hist_density": hist_density,
        "bin_edges": bin_edges,
        "bin_centers": bin_centers,
        "fit_x": np.asarray(bin_centers, dtype=float),
        "fit_y": np.asarray(hist_density, dtype=float),
    }


def build_valid_loglog_histogram_points(histogram, fit_label="power-law fit"):
    fit_x = np.asarray(histogram["fit_x"], dtype=float)
    fit_y = np.asarray(histogram["fit_y"], dtype=float)
    if fit_x.ndim != 1 or fit_y.ndim != 1 or fit_x.size != fit_y.size:
        raise ValueError(f"{fit_label}: histogram fit points must be matching 1D arrays.")

    valid_mask = np.isfinite(fit_x) & np.isfinite(fit_y) & (fit_x > 0) & (fit_y > 0)
    valid_x = fit_x[valid_mask]
    valid_y = fit_y[valid_mask]
    if valid_x.size == 0:
        raise ValueError(f"{fit_label}: histogram has no positive finite points available for log-log fitting.")

    sort_index = np.argsort(valid_x, kind="mergesort")
    return valid_x[sort_index], valid_y[sort_index]


def slice_histogram_fit_points(valid_x, valid_y, start, end, fit_label="power-law fit"):
    valid_x = np.asarray(valid_x, dtype=float)
    valid_y = np.asarray(valid_y, dtype=float)
    if valid_x.ndim != 1 or valid_y.ndim != 1 or valid_x.size != valid_y.size:
        raise ValueError(f"{fit_label}: histogram fit points must be matching 1D arrays.")
    if valid_x.size == 0:
        raise ValueError(f"{fit_label}: no histogram fit points are available for slicing.")
    if not isinstance(start, (int, np.integer)) or not isinstance(end, (int, np.integer)):
        raise TypeError(
            f"{fit_label}: histogram fit point slice indices must be integers, got start={start!r}, end={end!r}."
        )

    start = int(start)
    end = int(end)
    if start < 0 or end < 0:
        raise ValueError(
            f"{fit_label}: histogram fit point slice indices must be non-negative, got start={start}, end={end}."
        )
    if start >= end:
        raise ValueError(
            f"{fit_label}: invalid histogram fit point slice [{start}:{end}] under Python slice rules; "
            "start must be smaller than end."
        )
    if end > valid_x.size:
        raise ValueError(
            f"{fit_label}: histogram fit point slice [{start}:{end}] exceeds valid point count {valid_x.size}."
        )

    slice_x = valid_x[start:end]
    slice_y = valid_y[start:end]
    if slice_x.size < 2:
        raise ValueError(
            f"{fit_label}: histogram fit point slice [{start}:{end}] is too short for log-log regression; "
            "need at least 2 points."
        )
    if not np.all(slice_x > 0) or not np.all(slice_y > 0):
        raise ValueError(
            f"{fit_label}: histogram fit point slice [{start}:{end}] must contain only positive x and y values."
        )
    return slice_x, slice_y


def build_power_law_histogram_fit(valid_x, valid_y, start, end, label, points=400):
    fit_label = f"{label} [{start}:{end}]"
    slice_x, slice_y = slice_histogram_fit_points(valid_x, valid_y, start=start, end=end, fit_label=fit_label)

    log_x = np.log(slice_x)
    log_y = np.log(slice_y)
    slope, intercept = np.polyfit(log_x, log_y, deg=1)
    if not np.isfinite(slope) or not np.isfinite(intercept):
        raise ValueError(f"{fit_label}: log-log regression produced non-finite parameters.")

    x_min = float(slice_x.min())
    x_max = float(slice_x.max())
    if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min <= 0 or x_max <= 0:
        raise ValueError(f"{fit_label}: invalid positive x-range for plotting.")
    if x_max == x_min:
        x_max = x_min * 1.01

    x_grid = np.geomspace(x_min, x_max, int(points))
    coefficient = float(np.exp(intercept))
    y_grid = coefficient * np.power(x_grid, slope)
    if not np.all(np.isfinite(y_grid)):
        raise ValueError(f"{fit_label}: power-law curve contains non-finite values.")
    if not np.any(y_grid > 0):
        raise ValueError(f"{fit_label}: power-law curve is not positive on the plotting grid.")

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "coefficient": coefficient,
        "x_grid": x_grid,
        "y_grid": y_grid,
        "label": f"{label}: y = {coefficient:.2f} * x ^ {slope:.2f}",
        "start": int(start),
        "end": int(end),
        "fit_x": slice_x,
        "fit_y": slice_y,
    }


def select_signed_price_change_log_fit_points(histogram, x_min, x_max, fit_label="exponential fit"):
    fit_x = np.asarray(histogram["fit_x"], dtype=float)
    fit_y = np.asarray(histogram["fit_y"], dtype=float)
    if fit_x.ndim != 1 or fit_y.ndim != 1 or fit_x.size != fit_y.size:
        raise ValueError(f"{fit_label}: histogram fit points must be matching 1D arrays.")

    x_min = float(x_min)
    x_max = float(x_max)
    if not np.isfinite(x_min) or not np.isfinite(x_max):
        raise ValueError(f"{fit_label}: x_min and x_max must be finite.")
    if x_min >= x_max:
        raise ValueError(f"{fit_label}: x_min must be smaller than x_max, got x_min={x_min}, x_max={x_max}.")
    if x_min < 0 < x_max:
        raise ValueError(
            f"{fit_label}: signed x-range [{x_min}, {x_max}] crosses 0 and must stay on one side of the origin."
        )

    valid_mask = np.isfinite(fit_x) & np.isfinite(fit_y) & (fit_y > 0)
    valid_mask = valid_mask & (fit_x >= x_min) & (fit_x <= x_max)
    selected_x = fit_x[valid_mask]
    selected_y = fit_y[valid_mask]
    if selected_x.size < 2:
        raise ValueError(
            f"{fit_label}: signed x-range [{x_min}, {x_max}] leaves fewer than 2 positive finite histogram points."
        )

    sort_index = np.argsort(selected_x, kind="mergesort")
    return selected_x[sort_index], selected_y[sort_index]


def build_signed_price_change_exponential_curve(fit_x, fit_y, label, x_min, x_max, points=400):
    fit_x = np.asarray(fit_x, dtype=float)
    fit_y = np.asarray(fit_y, dtype=float)
    fit_label = f"{label} [{x_min:.6g}, {x_max:.6g}]"
    if fit_x.ndim != 1 or fit_y.ndim != 1 or fit_x.size != fit_y.size:
        raise ValueError(f"{fit_label}: fit_x and fit_y must be matching 1D arrays.")
    if fit_x.size < 2:
        raise ValueError(f"{fit_label}: exponential fitting requires at least 2 points.")
    if not np.all(np.isfinite(fit_x)) or not np.all(np.isfinite(fit_y)):
        raise ValueError(f"{fit_label}: exponential fitting requires finite fit points.")
    if not np.all(fit_y > 0):
        raise ValueError(f"{fit_label}: exponential fitting requires strictly positive y values.")

    slope, intercept = np.polyfit(fit_x, np.log(fit_y), deg=1)
    if not np.isfinite(slope) or not np.isfinite(intercept):
        raise ValueError(f"{fit_label}: log-linear regression produced non-finite parameters.")

    x_grid = np.linspace(float(fit_x.min()), float(fit_x.max()), int(points))
    y_grid = np.exp(intercept + slope * x_grid)
    if not np.all(np.isfinite(x_grid)) or not np.all(np.isfinite(y_grid)):
        raise ValueError(f"{fit_label}: exponential curve contains non-finite values.")
    if not np.all(y_grid > 0):
        raise ValueError(f"{fit_label}: exponential curve must stay strictly positive on the plotting grid.")

    amplitude = float(np.exp(intercept))
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "amplitude": amplitude,
        "x_grid": x_grid,
        "y_grid": y_grid,
        "label": f"{label} exponential fit: y = {amplitude:.2f} * exp({slope:.2f} * x)",
        "fit_x": fit_x,
        "fit_y": fit_y,
        "x_min": x_min,
        "x_max": x_max,
    }


def aligned_trade_volume(orderbook_window, trade_window, window_seconds):
    per_second = trade_volume_per_second(trade_window, window_seconds)
    aligned = align_on_time(orderbook_window["time_axis"], trade_window["trade_time"], per_second)
    if np.all(np.isnan(aligned)):
        raise ValueError(
            f"Trade window w{window_seconds} does not align with orderbook timestamps. "
            "Prepare preprocess artifacts with matching trade windows before running this block."
        )
    return aligned


def future_side_volume_series(reference_time, trade_time, trade_volume, trade_side, target_side, horizon_seconds):
    reference_time = pd.to_datetime(np.asarray(reference_time))
    trade_time = pd.to_datetime(np.asarray(trade_time))
    trade_volume = np.asarray(trade_volume, dtype=float)
    trade_side = np.asarray(trade_side, dtype=float)
    if target_side == "bid":
        side_mask = trade_side == -1
    elif target_side == "ask":
        side_mask = trade_side == 1
    else:
        raise ValueError(f"Unsupported target_side: {target_side!r}.")

    finite_mask = np.isfinite(trade_volume) & np.isfinite(trade_side)
    side_mask = side_mask & finite_mask
    filtered_trade_time = trade_time[side_mask]
    filtered_trade_volume = trade_volume[side_mask]
    result = np.zeros(len(reference_time), dtype=float)
    if len(filtered_trade_time) == 0:
        return result

    trade_time_ns = filtered_trade_time.view("i8")
    reference_time_ns = reference_time.view("i8")
    horizon_ns = pd.Timedelta(seconds=int(horizon_seconds)).value
    cumulative = np.concatenate(([0.0], np.cumsum(filtered_trade_volume, dtype=float)))
    start_index = np.searchsorted(trade_time_ns, reference_time_ns, side="left")
    end_index = np.searchsorted(trade_time_ns, reference_time_ns + horizon_ns, side="right")
    return cumulative[end_index] - cumulative[start_index]


def executed_ratio_series(current_queue_size, future_volume, clip_upper=1.0):
    current_queue_size = np.asarray(current_queue_size, dtype=float)
    future_volume = np.asarray(future_volume, dtype=float)
    ratio = np.full_like(current_queue_size, np.nan, dtype=float)
    valid_mask = np.isfinite(current_queue_size) & np.isfinite(future_volume) & (current_queue_size > 0)
    ratio[valid_mask] = future_volume[valid_mask] / current_queue_size[valid_mask]
    return np.clip(ratio, 0.0, clip_upper)


def build_symmetric_executed_ratio_samples(orderbook_window, trade_window, depth, horizon_seconds):
    bid_top_n, ask_top_n = depth_sizes(orderbook_window, depth)
    trade_time = trade_window["trade_time"]
    trade_volume = trade_window["trade_volume"]
    trade_side = trade_window["trade_side"]
    reference_time = orderbook_window["time_axis"]

    bid_future_volume = future_side_volume_series(
        reference_time,
        trade_time,
        trade_volume,
        trade_side,
        target_side="bid",
        horizon_seconds=horizon_seconds,
    )
    ask_future_volume = future_side_volume_series(
        reference_time,
        trade_time,
        trade_volume,
        trade_side,
        target_side="ask",
        horizon_seconds=horizon_seconds,
    )

    bid_ratio = executed_ratio_series(bid_top_n, bid_future_volume)
    ask_ratio = executed_ratio_series(ask_top_n, ask_future_volume)

    near_size = np.concatenate([bid_top_n, ask_top_n])
    opposite_size = np.concatenate([ask_top_n, bid_top_n])
    executed_ratio = np.concatenate([bid_ratio, ask_ratio])
    finite_mask = np.isfinite(near_size) & np.isfinite(opposite_size) & np.isfinite(executed_ratio)
    return near_size[finite_mask], opposite_size[finite_mask], executed_ratio[finite_mask]


def _imshow_heatmap(ax, matrix, fig_range, cmap, title, xlabel, ylabel, norm=None, vmin=None, vmax=None):
    display_matrix = np.ma.masked_invalid(np.asarray(matrix, dtype=float).T)
    heatmap_cmap = plt.get_cmap(cmap).copy()
    heatmap_cmap.set_bad(color="white")
    image = ax.imshow(
        display_matrix,
        origin="lower",
        extent=fig_range + fig_range,
        aspect="auto",
        cmap=heatmap_cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return image


def plot_mid_price(orderbook_by_window, base_window_for_correlation):
    base_orderbook = orderbook_by_window[base_window_for_correlation]
    mid_time = pd.to_datetime(base_orderbook["time_axis"])
    mid_price = np.asarray(base_orderbook["mid"], dtype=float)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(mid_time, mid_price)
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USD)")
    ax.set_title(f"Price vs. Time (w{base_window_for_correlation} mid)")
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return base_orderbook, mid_time, mid_price


def plot_future_price_change(mid_time, mid_price, price_change_horizons):
    price_change_by_horizon = {}
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    for ax, horizon_seconds in zip(axes.flat, price_change_horizons):
        price_change_time, price_change_values = calc_price_change_series(mid_time, mid_price, horizon_seconds)
        price_change_by_horizon[horizon_seconds] = {
            "time": pd.to_datetime(price_change_time),
            "price_change": np.asarray(price_change_values, dtype=float),
        }
        ax.plot(
            price_change_by_horizon[horizon_seconds]["time"],
            price_change_by_horizon[horizon_seconds]["price_change"],
        )
        ax.set_title(f"{horizon_seconds}s Future Price Change vs. Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price Change (USD)")
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return price_change_by_horizon


def plot_rolling_price_change_average(price_change_by_horizon, price_change_horizons, variance_windows):
    average_by_config = {}
    for average_window_seconds in variance_windows:
        fig, ax = plt.subplots(figsize=(12, 4))
        for horizon_seconds in price_change_horizons:
            price_change_series = price_change_by_horizon[horizon_seconds]
            average_time, average_values = calc_price_change_average_series(
                price_change_series["time"],
                price_change_series["price_change"],
                average_window_seconds,
            )
            average_by_config[(horizon_seconds, average_window_seconds)] = {
                "time": pd.to_datetime(average_time),
                "average": np.asarray(average_values, dtype=float),
            }
            ax.plot(
                average_by_config[(horizon_seconds, average_window_seconds)]["time"],
                average_by_config[(horizon_seconds, average_window_seconds)]["average"],
                label=f"average price change {horizon_seconds}s",
            )
        ax.set_xlabel("Time")
        ax.set_ylabel("Price Change Average")
        ax.set_title(f"Rolling Price Change Average ({average_window_seconds}s window)")
        ax.legend()
        fig.tight_layout()
        plt.ylim(-2, 2)
        plt.show()
        plt.close(fig)
    return average_by_config


def plot_rolling_price_change_variance(price_change_by_horizon, price_change_horizons, variance_windows):
    variance_by_config = {}
    for variance_window_seconds in variance_windows:
        fig, ax = plt.subplots(figsize=(12, 4))
        for horizon_seconds in price_change_horizons:
            price_change_series = price_change_by_horizon[horizon_seconds]
            variance_time, variance_values = calc_variance_series(
                price_change_series["time"],
                price_change_series["price_change"],
                variance_window_seconds,
            )
            variance_by_config[(horizon_seconds, variance_window_seconds)] = {
                "time": pd.to_datetime(variance_time),
                "variance": np.asarray(variance_values, dtype=float),
            }
            ax.plot(
                variance_by_config[(horizon_seconds, variance_window_seconds)]["time"],
                variance_by_config[(horizon_seconds, variance_window_seconds)]["variance"],
                label=f"price change {horizon_seconds}s",
            )
        ax.set_xlabel("Time")
        ax.set_ylabel("Price Change Variance")
        ax.set_title(f"Rolling Price Change Variance ({variance_window_seconds}s window)")
        ax.legend()
        fig.tight_layout()
        plt.show()
        plt.close(fig)
    return variance_by_config


def plot_spread_distribution(
    orderbook_by_window,
    window_seconds,
    normal_fit_config,
    power_law_fit_configs,
    hist_bins,
):
    if window_seconds not in orderbook_by_window:
        raise ValueError(f"Distribution requires orderbook window w{window_seconds}, but it is missing.")

    spread = spread_from_orderbook_window(orderbook_by_window[window_seconds])
    spread_tick = spread / 0.01
    spread_tick = spread_tick[np.isfinite(spread_tick) & (spread_tick > 0)]
    if spread_tick.size == 0:
        raise ValueError(f"Spread distribution has no positive finite observations for w{window_seconds}.")

    linear_histogram = build_density_histogram(
        spread_tick,
        bins=hist_bins,
        use_log_bins=False,
        fit_label=f"Spread distribution linear histogram (w{window_seconds})",
    )
    log_histogram = build_density_histogram(
        spread_tick,
        bins=hist_bins,
        use_log_bins=True,
        fit_label=f"Spread distribution log histogram (w{window_seconds})",
    )
    valid_x, valid_y = build_valid_loglog_histogram_points(
        log_histogram,
        fit_label=f"Spread distribution power-law fit (w{window_seconds})",
    )
    normal_samples = filter_spread_normal_fit_samples(
        spread_tick,
        x_min=normal_fit_config["x_min"],
        x_max=normal_fit_config["x_max"],
        fit_label=f"Spread distribution normal fit (w{window_seconds})",
    )
    normal_x, normal_pdf, spread_mean, spread_std = build_normal_fit_curve(normal_samples)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].stairs(linear_histogram["hist_density"], linear_histogram["bin_edges"], color="tab:blue", linewidth=1.2)
    if normal_x is not None:
        axes[0].plot(
            normal_x,
            normal_pdf,
            color=normal_fit_config["color"],
            linewidth=1.5,
            label=f"normal fit (mean={spread_mean:.2f}, std={spread_std:.2f})",
        )
    axes[0].set_xlabel("Spread (tick)")
    axes[0].set_ylabel("Density")
    axes[0].set_ylim(0, 0.2)
    axes[0].set_title(f"Spread Distribution (w{window_seconds}, linear scale)")

    axes[1].stairs(log_histogram["hist_density"], log_histogram["bin_edges"], color="tab:blue", linewidth=1.2)
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_ylim(1e-5, 1e2)
    if normal_x is not None:
        spread_log_mask = build_plot_curve_mask(normal_x, normal_pdf, require_positive_x=True)
        if np.any(spread_log_mask):
            axes[1].plot(
                normal_x[spread_log_mask],
                normal_pdf[spread_log_mask],
                color=normal_fit_config["color"],
                linewidth=1.5,
                label=f"normal fit (mean={spread_mean:.2f}, std={spread_std:.2f})",
            )
    axes[1].set_xlabel("Spread (tick)")
    axes[1].set_ylabel("Density")
    axes[1].set_title(f"Spread Distribution (w{window_seconds}, log scale)")

    fit_results = []
    for fit_config in power_law_fit_configs:
        fit_result = build_power_law_histogram_fit(
            valid_x,
            valid_y,
            start=fit_config["start"],
            end=fit_config["end"],
            label=fit_config["label"],
        )
        fit_results.append(fit_result)
        fit_color = fit_config["color"]
        axes[0].plot(fit_result["x_grid"], fit_result["y_grid"], color=fit_color, linewidth=1.5, label=fit_result["label"])
        log_fit_mask = build_plot_curve_mask(fit_result["x_grid"], fit_result["y_grid"], require_positive_x=True)
        if np.any(log_fit_mask):
            axes[1].plot(
                fit_result["x_grid"][log_fit_mask],
                fit_result["y_grid"][log_fit_mask],
                color=fit_color,
                linewidth=1.5,
                label=fit_result["label"],
            )

    for ax in axes:
        handles, _ = ax.get_legend_handles_labels()
        if handles:
            ax.legend()

    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return {
        "spread_tick": spread_tick,
        "linear_histogram": linear_histogram,
        "log_histogram": log_histogram,
        "power_law_fits": fit_results,
        "normal_fit": {
            "x": normal_x,
            "pdf": normal_pdf,
            "mean": spread_mean,
            "std": spread_std,
        },
    }


def plot_trade_volume_distribution(trade_by_window, window_seconds, fit_configs, hist_bins):
    if window_seconds not in trade_by_window:
        raise ValueError(f"Distribution requires trade window w{window_seconds}, but it is missing.")

    trade_volume = np.asarray(trade_by_window[window_seconds]["trade_volume"], dtype=float)
    trade_volume = trade_volume[np.isfinite(trade_volume) & (trade_volume > 0)]
    if trade_volume.size == 0:
        raise ValueError(f"Trade volume distribution has no positive finite observations for w{window_seconds}.")

    linear_histogram = build_density_histogram(
        trade_volume,
        bins=hist_bins,
        use_log_bins=False,
        fit_label=f"Trade volume distribution linear histogram (w{window_seconds})",
    )
    log_histogram = build_density_histogram(
        trade_volume,
        bins=hist_bins,
        use_log_bins=True,
        fit_label=f"Trade volume distribution log histogram (w{window_seconds})",
    )
    valid_x, valid_y = build_valid_loglog_histogram_points(
        log_histogram,
        fit_label=f"Trade volume distribution power-law fit (w{window_seconds})",
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].stairs(linear_histogram["hist_density"], linear_histogram["bin_edges"], color="tab:orange", linewidth=1.2)
    axes[0].set_xlabel("Trade Volume")
    axes[0].set_ylabel("Density")
    axes[0].set_ylim(0, 0.002)
    axes[0].set_title(f"Trade Volume Distribution (w{window_seconds}, linear scale)")

    axes[1].stairs(log_histogram["hist_density"], log_histogram["bin_edges"], color="tab:orange", linewidth=1.2)
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Trade Volume")
    axes[1].set_ylabel("Density")
    axes[1].set_title(f"Trade Volume Distribution (w{window_seconds}, log scale)")

    fit_results = []
    for fit_config in fit_configs:
        fit_result = build_power_law_histogram_fit(
            valid_x,
            valid_y,
            start=fit_config["start"],
            end=fit_config["end"],
            label=fit_config["label"],
        )
        fit_results.append(fit_result)
        log_fit_mask = build_plot_curve_mask(fit_result["x_grid"], fit_result["y_grid"], require_positive_x=True)
        if np.any(log_fit_mask):
            axes[1].plot(
                fit_result["x_grid"][log_fit_mask],
                fit_result["y_grid"][log_fit_mask],
                color=fit_config["color"],
                linewidth=1.5,
                label=fit_result["label"],
            )

    for ax in axes:
        handles, _ = ax.get_legend_handles_labels()
        if handles:
            ax.legend()

    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return {
        "trade_volume": trade_volume,
        "linear_histogram": linear_histogram,
        "log_histogram": log_histogram,
        "power_law_fits": fit_results,
    }


def plot_price_change_distribution(price_change_by_horizon, price_change_horizons, exponential_fit_configs, hist_bins):
    distribution_by_horizon = {}
    fig, axes = plt.subplots(len(price_change_horizons), 2, figsize=(14, 4 * len(price_change_horizons)))
    axes = np.atleast_2d(axes)
    for row_index, horizon_seconds in enumerate(price_change_horizons):
        linear_ax = axes[row_index, 0]
        log_ax = axes[row_index, 1]

        price_change_values = np.asarray(price_change_by_horizon[horizon_seconds]["price_change"], dtype=float)
        price_change_values = price_change_values[np.isfinite(price_change_values)]
        if price_change_values.size == 0:
            raise ValueError(f"Price change distribution has no finite observations for horizon {horizon_seconds}s.")

        histogram = build_density_histogram(
            price_change_values,
            bins=hist_bins,
            use_log_bins=False,
            fit_label=f"Price change distribution histogram ({horizon_seconds}s horizon)",
        )
        normal_x, normal_pdf, normal_mean, normal_std = build_normal_fit_curve(price_change_values)

        linear_ax.stairs(histogram["hist_density"], histogram["bin_edges"], color="tab:green", linewidth=1.2)
        if normal_x is not None:
            linear_ax.plot(
                normal_x,
                normal_pdf,
                color="tab:orange",
                linewidth=1.5,
                label=f"normal fit (mean={normal_mean:.4f}, std={normal_std:.4f})",
            )
        linear_ax.set_xlabel("Price Change (USD)")
        linear_ax.set_ylabel("Density")
        linear_ax.set_title(f"Price Change Distribution ({horizon_seconds}s horizon, linear scale)")

        log_ax.stairs(histogram["hist_density"], histogram["bin_edges"], color="tab:green", linewidth=1.2)
        log_ax.set_yscale("log")
        if normal_x is not None:
            normal_log_mask = build_plot_curve_mask(normal_x, normal_pdf, require_positive_x=False)
            if np.any(normal_log_mask):
                log_ax.plot(
                    normal_x[normal_log_mask],
                    normal_pdf[normal_log_mask],
                    color="tab:orange",
                    linewidth=1.5,
                    label=f"normal fit (mean={normal_mean:.4f}, std={normal_std:.4f})",
                )

        fit_results = []
        for fit_config in exponential_fit_configs.get(horizon_seconds, []):
            fit_x, fit_y = select_signed_price_change_log_fit_points(
                histogram,
                x_min=fit_config["x_min"],
                x_max=fit_config["x_max"],
                fit_label=f"{fit_config['label']} ({horizon_seconds}s horizon)",
            )
            fit_result = build_signed_price_change_exponential_curve(
                fit_x,
                fit_y,
                label=fit_config["label"],
                x_min=fit_config["x_min"],
                x_max=fit_config["x_max"],
            )
            fit_results.append(fit_result)
            log_fit_mask = build_plot_curve_mask(
                fit_result["x_grid"],
                fit_result["y_grid"],
                require_positive_x=False,
            )
            if np.any(log_fit_mask):
                log_ax.plot(
                    fit_result["x_grid"][log_fit_mask],
                    fit_result["y_grid"][log_fit_mask],
                    color=fit_config["color"],
                    linewidth=1.5,
                    label=fit_result["label"],
                )

        linear_handles, _ = linear_ax.get_legend_handles_labels()
        if linear_handles:
            linear_ax.legend()

        log_handles, _ = log_ax.get_legend_handles_labels()
        if log_handles:
            log_ax.legend()

        log_ax.set_xlabel("Price Change (USD)")
        log_ax.set_ylabel("Density (log scale)")
        log_ax.set_ylim(1e-4, 1e2)
        log_ax.set_title(f"Price Change Distribution ({horizon_seconds}s horizon, log y-scale)")
        distribution_by_horizon[horizon_seconds] = {
            "values": price_change_values,
            "histogram": histogram,
            "normal_fit": {
                "x": normal_x,
                "pdf": normal_pdf,
                "mean": normal_mean,
                "std": normal_std,
            },
            "exponential_fits": fit_results,
        }

    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return distribution_by_horizon


def plot_executed_ratio_heatmap(
    orderbook_by_window,
    trade_by_window,
    base_window_for_correlation,
    horizons,
    depth,
    heatmap_range,
    heatmap_bins,
):
    base_orderbook = orderbook_by_window[base_window_for_correlation]
    base_trade = trade_by_window[base_window_for_correlation]
    executed_ratio_heatmaps = {}
    for horizon_seconds in horizons:
        near_size, opposite_size, executed_ratio = build_symmetric_executed_ratio_samples(
            base_orderbook,
            base_trade,
            depth=depth,
            horizon_seconds=horizon_seconds,
        )
        if len(executed_ratio) == 0:
            raise ValueError(f"Executed ratio heatmap has no finite observations for horizon {horizon_seconds}s.")

        executed_ratio_heat, _, _ = mean_2d_binned(
            near_size,
            opposite_size,
            executed_ratio,
            bins=heatmap_bins,
            fig_range=heatmap_range,
        )
        executed_ratio_heatmaps[horizon_seconds] = executed_ratio_heat

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True, constrained_layout=True)
    last_image = None
    for ax, horizon_seconds in zip(axes.flat, horizons):
        last_image = _imshow_heatmap(
            ax,
            executed_ratio_heatmaps[horizon_seconds],
            heatmap_range,
            "viridis",
            f"Executed Ratio Heatmap (top-{depth} queue, {horizon_seconds}s horizon)",
            "Near Size",
            "Opposite Size",
            vmin=0.0,
            vmax=1.0,
        )

    fig.colorbar(last_image, ax=axes, label="Executed Ratio", shrink=0.92)
    plt.show()
    plt.close(fig)
    return base_orderbook, base_trade, executed_ratio_heatmaps


def plot_average_price_change_heatmap(
    base_orderbook,
    price_change_by_horizon,
    price_change_horizons,
    heatmap_range,
    heatmap_bins,
    heatmap_cmap,
    abs_limit,
):
    price_change_norm = build_symmetric_two_slope_norm(abs_limit)
    base_bid_size, base_ask_size = top_level_sizes(base_orderbook)
    avg_price_change_heatmaps = {}
    for horizon_seconds in price_change_horizons:
        price_change_series = price_change_by_horizon[horizon_seconds]
        aligned_bid_size = align_on_time(price_change_series["time"], base_orderbook["time_axis"], base_bid_size)
        aligned_ask_size = align_on_time(price_change_series["time"], base_orderbook["time_axis"], base_ask_size)
        mask = (
            np.isfinite(aligned_bid_size)
            & np.isfinite(aligned_ask_size)
            & np.isfinite(price_change_series["price_change"])
        )
        if not np.any(mask):
            raise ValueError(
                f"Average price change heatmap has no aligned finite observations for horizon {horizon_seconds}s."
            )

        avg_price_change_heat, _, _ = mean_2d_binned(
            aligned_bid_size[mask],
            aligned_ask_size[mask],
            price_change_series["price_change"][mask],
            bins=heatmap_bins,
            fig_range=heatmap_range,
        )
        if not np.isfinite(avg_price_change_heat).any():
            raise ValueError(
                f"Average price change heatmap has no finite values after 2D binning for horizon {horizon_seconds}s."
            )
        avg_price_change_heatmaps[horizon_seconds] = avg_price_change_heat

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True, constrained_layout=True)
    last_image = None
    for ax, horizon_seconds in zip(axes.flat, price_change_horizons):
        last_image = _imshow_heatmap(
            ax,
            avg_price_change_heatmaps[horizon_seconds],
            heatmap_range,
            heatmap_cmap,
            f"Average Price Change Heatmap ({horizon_seconds}s horizon)",
            "Bid Size",
            "Ask Size",
            norm=price_change_norm,
        )

    fig.colorbar(last_image, ax=axes, label="Average Price Change (USD)", shrink=0.92)
    plt.show()
    plt.close(fig)
    return avg_price_change_heatmaps, price_change_norm


def plot_fill_volume_correlation_heatmap(orderbook_by_window, trade_by_window, orderbook_windows):
    feature_rows = ["spread", "near_volume", "opposite_volume", "imbalance"]
    column_labels = [f"{window_seconds}s" for window_seconds in orderbook_windows]
    corr_matrix = pd.DataFrame(index=feature_rows, columns=column_labels, dtype=float)

    for window_seconds in orderbook_windows:
        orderbook_window = orderbook_by_window[window_seconds]
        trade_window = trade_by_window[window_seconds]

        fill_volume_per_second = aligned_trade_volume(orderbook_window, trade_window, window_seconds)
        spread = spread_from_orderbook_window(orderbook_window)
        near_volume, opposite_volume = top_level_sizes(orderbook_window)
        near_volume = np.asarray(near_volume, dtype=float)
        opposite_volume = np.asarray(opposite_volume, dtype=float)
        denominator = near_volume + opposite_volume
        imbalance = np.divide(
            near_volume - opposite_volume,
            denominator,
            out=np.full_like(denominator, np.nan, dtype=float),
            where=denominator != 0,
        )

        correlation_frame = pd.DataFrame(
            {
                "fill_volume_per_second": fill_volume_per_second,
                "spread": spread,
                "near_volume": near_volume,
                "opposite_volume": opposite_volume,
                "imbalance": imbalance,
            }
        ).dropna()

        if correlation_frame.empty:
            raise ValueError(
                f"Fill volume correlation block has no aligned observations after dropping NaNs for window w{window_seconds}."
            )

        column_label = f"{window_seconds}s"
        for row_label in feature_rows:
            corr_matrix.loc[row_label, column_label] = correlation_frame["fill_volume_per_second"].corr(
                correlation_frame[row_label]
            )

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(corr_matrix, annot=True, fmt=".4f", center=0, cmap="coolwarm", ax=ax)
    ax.set_xlabel("Fill volume per second")
    ax.set_ylabel("Feature")
    ax.set_title("Fill Volume Per Second Correlation Heatmap")
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    return corr_matrix


def plot_cross_correlation_heatmap(
    orderbook_by_window,
    base_window_for_correlation,
    price_change_by_horizon,
    variance_by_config,
    price_change_horizons,
    variance_windows,
    depths,
):
    base_orderbook = orderbook_by_window[base_window_for_correlation]
    aligned_time_axis = base_orderbook["time_axis"]
    depth_features = {}
    for depth in depths:
        bid_size, ask_size = depth_sizes(base_orderbook, depth)
        bid_size = np.asarray(bid_size, dtype=float)
        ask_size = np.asarray(ask_size, dtype=float)
        denom = bid_size + ask_size
        imbalance = np.divide(
            bid_size - ask_size,
            denom,
            out=np.full_like(denom, np.nan, dtype=float),
            where=denom != 0,
        )
        depth_features[depth] = {
            "bid": bid_size,
            "ask": ask_size,
            "imb": np.asarray(imbalance, dtype=float),
        }

    ordered_labels = []
    ordered_labels.extend(f"price_change_{h}" for h in price_change_horizons)
    ordered_labels.extend(f"variance_{h}" for h in price_change_horizons)
    ordered_labels.extend(f"imb_levels_{depth}" for depth in depths)
    ordered_labels.extend(f"bid_size_levels_{depth}" for depth in depths)
    ordered_labels.extend(f"ask_size_levels_{depth}" for depth in depths)

    corr_matrix_by_variance_window = {}
    for variance_window_seconds in variance_windows:
        base_variance_series = variance_by_config[(price_change_horizons[0], variance_window_seconds)]
        if len(base_variance_series["time"]) == 0:
            raise ValueError(
                f"Cross correlation requires non-empty variance data for variance window {variance_window_seconds}s."
            )

        base_index = pd.to_datetime(base_variance_series["time"])
        corr_frame = pd.DataFrame(index=base_index)

        for horizon_seconds in price_change_horizons:
            price_change_series = price_change_by_horizon[horizon_seconds]
            corr_frame[f"price_change_{horizon_seconds}"] = align_on_time(
                base_index,
                price_change_series["time"],
                price_change_series["price_change"],
            )

            variance_series = variance_by_config[(horizon_seconds, variance_window_seconds)]
            corr_frame[f"variance_{horizon_seconds}"] = align_on_time(
                base_index,
                variance_series["time"],
                variance_series["variance"],
            )

        for depth in depths:
            corr_frame[f"imb_levels_{depth}"] = align_on_time(base_index, aligned_time_axis, depth_features[depth]["imb"])
            corr_frame[f"bid_size_levels_{depth}"] = align_on_time(
                base_index,
                aligned_time_axis,
                depth_features[depth]["bid"],
            )
            corr_frame[f"ask_size_levels_{depth}"] = align_on_time(
                base_index,
                aligned_time_axis,
                depth_features[depth]["ask"],
            )

        corr_matrix = corr_frame[ordered_labels].dropna().corr()
        if corr_matrix.empty:
            raise ValueError(
                f"Cross correlation block has no aligned observations after dropping NaNs for variance window {variance_window_seconds}s."
            )

        corr_matrix_by_variance_window[variance_window_seconds] = corr_matrix
        fig, ax = plt.subplots(figsize=(14, 12))
        sns.heatmap(
            corr_matrix,
            xticklabels=ordered_labels,
            yticklabels=ordered_labels,
            center=0,
            cmap="coolwarm",
            ax=ax,
        )
        ax.set_title(f"Cross Correlation Heatmap (variance window {variance_window_seconds}s)")
        fig.tight_layout()
        plt.show()
        plt.close(fig)

    return corr_matrix_by_variance_window

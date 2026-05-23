# `src.plotlib` API Reference

This document covers the APIs that other modules should depend on. Helpers inside `renderers/` are internal implementation details unless they are explicitly exported.

## Public entrypoint

[`src/plotlib/__init__.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/__init__.py) exports three categories:

- payload and schema types
- render option dataclasses
- plot builder functions

## Plot builders

All public builders are defined in [`src/plotlib/views.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/views.py). `__init__.py` re-exports them.

### `build_orderbook_view(payloads, render_options=None)`

- Input: `list[OrderbookPayloadV1]`
- Output: `holoviews` overlay
- Notes:
  - supports multiple batches
  - requires a single `product_id`
  - inserts `NaN` separators across time gaps between batches

### `build_trades_scatter_view(trade_frames_or_payloads, render_options=None)`

- Input: `Sequence[TradesPayloadV1 | pandas.DataFrame]`
- Output: `plotly.graph_objects.Figure`
- DataFrame requirements:
  - columns: `Time`, `Price`, `Volume`, `Side`
  - `DataFrame.attrs["product_id"]` must exist

### `build_trade_volume_timeline_view(trade_frames_or_payloads, render_options=None)`

- Input: `Sequence[TradesPayloadV1 | pandas.DataFrame]`
- Output: `plotly.graph_objects.Figure`

### `build_fill_probability_view(simulation_arrays, render_options=None)`

- Input: `SimulationArraysV1`
- Output: `plotly.graph_objects.Figure`
- Settings:
  - `render_options.simulation_heatmap_settings` should be `FillProbabilityPlotSettings`

### `build_mid_profit_view(simulation_arrays, render_options=None)`

- Input: `SimulationArraysV1`
- Output: `plotly.graph_objects.Figure`
- Settings:
  - `render_options.simulation_heatmap_settings` should be `ProfitPlotSettings`

### `build_micro_profit_view(simulation_arrays, render_options=None)`

- Same contract as `build_mid_profit_view`, but uses `micro_profit`

### `build_mid_cost_fill_probability_view(simulation_arrays, render_options=None)`

- Input: `SimulationArraysV1`
- Output: `plotly.graph_objects.Figure`
- Extra requirements:
  - `render_options.cost` must not be `None`
  - `render_options.simulation_heatmap_settings` should be `ConditionalFillProbabilityPlotSettings`

### `build_micro_cost_fill_probability_view(simulation_arrays, render_options=None)`

- Same contract as `build_mid_cost_fill_probability_view`, but uses `micro_profit`

## Payload schema

Schemas are defined in [`src/plotlib/types.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/types.py).

The current version is only `schema_version == "1"`.

### `OrderbookPayloadV1`

Required fields:

- `schema_version`
- `product_id`
- `timestamp`
- `time_step`
- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

Notes:

- `normalize_orderbook_payload_to_v1()` allows missing `mid` and backfills it with `(bid + ask) / 2`.
- the renderer converts `data` to signed log volume:
  - `sign(volume) * log1p(abs(volume))`

### `TradesPayloadV1`

Required fields:

- `schema_version`
- `product_id`
- `timestamp`
- `time_step`
- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

Notes:

- the loader converts `trade_time` into a `datetime64` array
- the renderer interprets `trade_side == -1.0` as `buy taker`
- the renderer interprets `trade_side == 1.0` as `sell taker`

### `SimulationArraysV1`

Required fields:

- `schema_version`
- `bid_near_size`
- `bid_opp_size`
- `bid_result`
- `ask_near_size`
- `ask_opp_size`
- `ask_result`
- `bid_mid_profit`
- `ask_mid_profit`
- `bid_micro_profit`
- `ask_micro_profit`

Notes:

- the simulation loader accepts multiple `.npz` files and concatenates each array field
- with `RESOLVED_ONLY = True`, `result == -1` is excluded from fill-probability style plots
- profit heatmaps only include samples with `result == 1`

## Loaders

Loaders live in [`src/plotlib/loaders/`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/loaders).

### `load_orderbook_payload(path, *, product_id, timestamp, time_step)`

- loads one `.npz`
- required keys:
  - `price_axis`
  - `time_axis`
  - `data`
  - `bid`
  - `ask`
- optional key:
  - `mid`

### `load_orderbook_payloads(datasets)`

- loads multiple orderbook datasets
- input shape:
  - `list[tuple[path, product_id, timestamp, time_step]]`

### `load_trades_payload(path, *, product_id, timestamp, time_step)`

- loads trade arrays from the preprocessed dataset `.npz`
- required keys:
  - `trade_time`
  - `trade_price`
  - `trade_volume`
  - `trade_side`

### `load_trades_payloads(datasets)`

- same dataset tuple input as `load_orderbook_payloads()`
- returns normalized trade payloads

### `load_simulation_arrays(paths)`

- loads one or many simulation `.npz` files
- concatenates each required array
- empty input returns empty arrays instead of raising immediately

## Render options

Options are defined in [`src/plotlib/options.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/options.py).

### `HeatmapAxisSettings`

- `size_min=1e-3`
- `size_max=10.0`
- `shared_bins=20`
- `use_log_bins=True`

Purpose:

- controls simulation heatmap axis ranges and binning

### `ManualColorRange`

- fixed `min` and `max`

Used by:

- fill-probability metric range

### `OptionalColorRange`

- `auto=True` lets the renderer choose the range
- `auto=False` uses `min` and `max`

Used by:

- sample-count color scales

### `OptionalSymmetricColorRange`

- `auto=True` lets the renderer pick a symmetric bound
- `auto=False` uses `limit` and applies `[-limit, limit]`

Used by:

- profit heatmaps

### `FillProbabilityPlotSettings`

- `axis`
- `metric_range`
- `sample_count_range`

### `ProfitPlotSettings`

- `axis`
- `metric_limit`
- `sample_count_range`

### `ConditionalFillProbabilityPlotSettings`

- `axis`
- `metric_range`
- `sample_count_range`

### `DashboardSimulationHeatmapSettings`

Purpose:

- serialization model for dashboard settings

Methods:

- `to_dict()`
- `from_dict(payload)`

### `PlotRenderOptions`

Fields:

- `cost: float | None`
- `simulation_heatmap_settings: SimulationHeatmapSettings | None`

Notes:

- `cost` only matters for cost-filtered fill probability plots
- each builder checks the concrete settings type it needs and falls back to defaults on mismatch

## Discovery helpers

[`src/plotlib/discovery.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/discovery.py) provides helpers for simulation output filenames.

Main APIs:

- `format_time_step(time_step)`
- `parse_simulation_filename(filename)`
- `find_simulation_files(...)`

Purpose:

- locate matching simulation files in `data/preprocessed`
- tolerate formatting differences in `time_step` and `resolved_time` tokens

## Errors

[`src/plotlib/errors.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/plotlib/errors.py) currently defines two domain-specific errors:

### `PayloadSchemaVersionError`

- raised when a payload `schema_version` does not match renderer expectations

### `PreprocessedDataError`

- raised when a `.npz` file cannot be loaded or is corrupted

Callers should still expect other standard exceptions:

- `FileNotFoundError`
- `KeyError`
- `ValueError`
- `PayloadSchemaVersionError`
- `PreprocessedDataError`

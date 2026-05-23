# Preprocess Module Reference

## `src/preprocess/__init__.py`

This file defines the package-level public API. New callers should import from `src.preprocess`, not from internal modules, unless they need implementation details.

Example:

```python
from src.preprocess import (
    DEFAULT_TIME_STEP,
    discover_preprocessed_datasets,
    discover_raw_batches,
    preprocess_batches,
)
```

## `src/preprocess/models.py`

This module defines the data objects shared by discovery, preprocessing, and rendering.

### `RawBatch`

Represents one complete raw CSV batch.

Fields:

- `product_id`
- `timestamp`
- `init_path`
- `updates_path`
- `trade_path`
- `is_preprocessed`

Computed properties:

- `batch_id`
  - `"<product_id>|<timestamp>"`
- `display_name`
  - Dashboard-facing label such as `ETH-USD | 2026-05-23 12:00:00 | preprocessed`

### `PreprocessedDataset`

Represents one plottable dataset entry discovered from `.npz` files.

Fields:

- `product_id`
- `timestamp`
- `time_step`
- `path`
- `available_views`
- `time_step_token`
- `resolved_time`
- `resolved_time_token`
- `algorithm_name`
- `simulation_path`

Important behavior:

- If `simulation_path is None`, this is a plain preprocessed orderbook dataset.
- If `simulation_path` exists, this dataset represents an orderbook dataset joined with one specific simulation file.
- `dataset_id` is path-based, and appends `#<simulation file>` for simulation-backed entries.
- `to_locator()` converts the dataset into a `PlotDatasetLocator` used by plot builders.

### `PlotDatasetLocator`

This is the object handed to plot builders. It keeps only the information needed during rendering:

- dataset identity
- preprocess directory
- optional simulation metadata
- optional payload cache

`path` resolves to:

- `original_path` when the locator came from a discovered dataset, otherwise
- `<preprocessed_dir>/<base_id>-orderbook_for_plot.npz`

### `PreprocessContext`

The builder input object used during preprocessing.

Fields:

- `batch`
- `time_step`
- `init_rows`
- `updates_rows`
- `trade_rows`

Builders receive already-loaded numeric CSV rows through this object.

## `src/preprocess/datasets.py`

This module combines three concerns:

1. Filename parsing and normalization
2. Catalog discovery
3. Preprocessed payload loading and schema validation

### Key functions

#### `format_time_step(time_step)`

Returns a stable decimal token for filenames and labels.

Examples:

- `0.01 -> "0.01"`
- `1.0 -> "1"`
- `Decimal("0.1000") -> "0.1"`

Raises `PreprocessValidationError` for non-finite or non-positive values.

#### `parse_timestamp(timestamp)`

Parses `yyyymmdd.hhmmss` into `datetime`.

#### `discover_raw_batches(raw_dir, preprocessed_dir)`

Scans `raw_dir` for matching raw CSV triples and returns complete `RawBatch` objects only.

Behavior:

- incomplete triples are ignored
- `is_preprocessed` becomes `True` when a matching orderbook `.npz` exists in `preprocessed_dir`
- simulation-only files do not mark a raw batch as preprocessed

#### `discover_preprocessed_datasets(preprocessed_dir, view_specs=None, simulation_view_keys=...)`

Scans `.npz` files and returns `PreprocessedDataset` entries.

Behavior:

- orderbook `.npz` files contribute base datasets
- simulation `.npz` files are attached by matching product, timestamp, and time step
- if an orderbook file exists with multiple simulation files, one dataset entry is produced per simulation file
- if a simulation file exists without an orderbook file, it still becomes a dataset entry, using the simulation file as `path`
- `available_views` are ordered by `DEFAULT_VIEW_ORDER`

#### `find_simulation_files(...)`

Finds matching simulation files for a given product, timestamp, and time step. It tolerates token differences such as `1`, `1.0`, or normalized decimal forms.

#### `has_simulation_file(...)`

Convenience wrapper over `find_simulation_files(...)`.

#### `detect_available_views(path, view_specs=None)`

Infers which plot views a `.npz` file supports.

Behavior:

- if `available_views` is explicitly stored in the file, it is used
- otherwise the function infers supported views from required payload keys
- if detection fails because the file is unreadable, `PreprocessedDataFileError` is raised
- if no views are detected, it falls back to `("orderbook",)`

#### `load_preprocessed_payload(dataset)`

Loads `.npz` content into memory and validates that orderbook schema fields exist and align.

Added metadata in returned payload:

- `product_id`
- `timestamp`
- `time_step`
- `available_views` for `PreprocessedDataset`

If the caller passes a `PlotDatasetLocator` with `payload_cache`, the result is cached by path.

### Schema validation

`_validate_preprocessed_payload_schema()` currently requires:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

It checks:

- `price_axis` and `time_axis` are 1D
- `data` is 2D
- `bid` and `ask` are 1D
- `bid.shape == ask.shape`
- data dimensions line up with both axes

## `src/preprocess/service.py`

This module is the preprocess execution layer.

### `DEFAULT_TIME_STEP`

Default preprocess sampling interval: `0.01` seconds.

### `read_csv_rows(path)`

Loads a CSV file with `csv.QUOTE_NONNUMERIC`, returning `list[list[float]]`.

This means the preprocess layer expects raw CSV files to already be numeric and headerless.

### `build_context(batch, time_step)` / `build_preprocess_context(...)`

Loads all three raw CSV files and returns a `PreprocessContext`.

`build_preprocess_context()` is currently a compatibility alias around `build_context()`.

### `build_trade_arrays(trade_rows, timestamp)`

Converts raw trade rows into four NumPy arrays:

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

The first column is interpreted as seconds from midnight of the batch date.

### `build_trade_payload(context)`

Produces the trade payload chunk used by:

- `trades_scatter`
- `trade_volume_timeline`

### `_merge_payload_chunk(base_payload, chunk)`

Combines builder outputs into one payload.

Conflict rule:

- identical values are accepted
- differing values for the same key raise `PreprocessOutputConflictError`

For NumPy arrays, equality is checked by shape and `np.array_equal(..., equal_nan=True)`.

### `preprocess_batch(batch, output_dir, time_step=..., builder_registry=None)`

This is the main write path.

Steps:

1. Build `PreprocessContext`.
2. Resolve builder registry from `src.plots.registry.PLOT_REGISTRY` if not provided.
3. Execute every `preprocess_builder` in registry order.
4. Skip builders whose returned chunk does not contain all `required_payload_keys`.
5. Merge payload chunks into one dict.
6. Save one compressed `.npz` file atomically via a temporary file.
7. Rediscover datasets from disk and return the matching `PreprocessedDataset`.

Output filename:

- `<product>-<timestamp>-<time_step>-orderbook_for_plot.npz`

### `preprocess_batches(...)`

Simple batch wrapper over `preprocess_batch()`.

Behavior:

- preserves input order
- emits progress messages when `progress_callback` is provided
- returns a list of discovered `PreprocessedDataset` results

## `src/preprocess/orderbook.py`

This module implements the orderbook-specific builder.

### `update_orderbook(orderbook, price_levels, price, volume, side)`

Applies one level update into the signed orderbook array.

The stored convention is:

- buy side becomes positive
- sell side becomes negative

because the implementation uses `volume * side * -1`.

### `get_bid_ask(orderbook, price_levels)`

Scans the signed orderbook array and derives:

- best bid
- best ask

If one side is missing, the returned value can be `np.nan`.

### `build_orderbook_history(init_rows, update_rows, start_time, time_step)`

Builds sampled orderbook history arrays:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

Important details:

- price levels are the union of initial levels and all update prices
- updates are sorted before replay
- samples begin only after the first update has been applied
- one final sample is appended after the replay loop

### `build_orderbook_payload(context)`

Package-facing preprocess builder used by the plot registry.

Returned keys:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

## `src/preprocess/exceptions.py`

Exception hierarchy:

- `PreprocessError`
  - base package error
- `PreprocessValidationError`
  - invalid time step or resolved time input
- `PreprocessOutputConflictError`
  - two builders emitted incompatible values for the same payload key
- `PreprocessedDataError`
  - base read/validation error for `.npz` content
- `PreprocessedDataFileError`
  - unreadable or invalid `.npz` file
- `PreprocessedDataSchemaError`
  - readable file, but missing or incompatible required fields

# Preprocess Module Reference

## `src/preprocess/__init__.py`

Public re-export surface for preprocess orchestration:

- `DEFAULT_DEPTH`
- `PLOT_REGISTRY`
- `PreprocessContext`
- `PreprocessBuilderSpec`
- `preprocess_batch(...)`
- `preprocess_batches(...)`
- `PreprocessError`
- `PreprocessValidationError`

## `src/preprocess/pipeline.py`

Owns the preprocess pipeline that turns one raw batch into one or more `.npz` datasets.

### Constants

- `DEFAULT_DEPTH`
  - Default orderbook depth used when the caller does not provide one.

### Data Models

- `PreprocessContext`
  - `batch`
  - `depth`
  - `trade_window_seconds`
  - `start_time`
  - `init_rows`
  - `updates_rows`
  - `trades_rows`
- `PreprocessBuilderSpec`
  - `preprocess_type`
  - `preprocess_builder`
  - `required_payload_keys`
  - `available_views`

### Functions

- `_validate_depth(depth)`
  - Rejects non-positive or non-integer depth values.
- `_validate_trade_window_seconds(value)`
  - Rejects non-positive or non-integer trade window values.
- `build_preprocess_context(batch, depth, loaded_batch=None, trade_window_seconds=1)`
  - Loads a raw batch and normalizes it into a `PreprocessContext`.
- `_save_preprocess_payload(...)`
  - Writes payload data and metadata into a compressed `.npz` file and rediscovers the written artifact.
  - For `trade`, merges the incoming `trade_*__wN` payload into the existing `preprocess-trade-*.npz` file before atomically replacing it.
  - For `orderbook`, merges the incoming orderbook `*__wN` payload into the existing `preprocess-orderbook-*.npz` file before atomically replacing it.
- `_load_existing_npz(path)`
  - Loads all existing keys from an existing preprocess `.npz` so unknown keys can be preserved during a window merge.
- `_merge_trade_payload(existing, payload, metadata)`
  - Replaces only the matching `trade_*__wN` keys, preserves other `trade_*__wM` versions, updates `trade_window_seconds_available`, and records `trade_window_seconds_latest`.
- `_merge_orderbook_payload(existing, payload, metadata)`
  - Replaces only the matching orderbook `*__wN` keys, preserves other orderbook `*__wM` versions, updates `orderbook_window_seconds_available`, records `orderbook_window_seconds_latest`, and drops legacy unsuffixed orderbook keys.
- `preprocess_batch(batch, output_dir, depth=DEFAULT_DEPTH, builder_registry=None, preprocess_timestamp=None, trade_window_seconds=1)`
  - Runs every registered preprocess builder for a single raw batch.
  - Defaults `preprocess_timestamp` to `batch.timestamp`.
- `preprocess_batches(batches, output_dir, depth=DEFAULT_DEPTH, builder_registry=None, progress_callback=None, preprocess_timestamp=None, trade_window_seconds=1)`
  - Processes multiple raw batches and reports progress if requested.
  - Uses each batch's `timestamp` unless the caller explicitly overrides `preprocess_timestamp`.

### `PLOT_REGISTRY`

The current registry contains two preprocess builders:

```python
{
    "orderbook": PreprocessBuilderSpec(
        preprocess_type="orderbook",
        ...,
        available_views=("orderbook",),
    ),
    "trade": PreprocessBuilderSpec(
        preprocess_type="trade",
        ...,
        available_views=("trades_scatter", "trade_volume_timeline"),
    ),
}
```

This registry determines:

- Which preprocess dataset files are written.
- Which payload keys are required for a builder to count as successful.
- Which view names are embedded into `available_views`.

The `orderbook` and `trade` builders no longer use fixed required payload keys because the written keys depend on `trade_window_seconds` and are emitted as versioned `*__wN` arrays.

## `src/preprocess/orderbook.py`

Builds the orderbook dataset payload.

### Functions

- `update_orderbook(orderbook, price_index, bid_indices, ask_indices, price, volume, side)`
  - Applies one level update and keeps the active bid and ask index lists synchronized in sorted order.
- `get_bid_ask(price_levels, bid_indices, ask_indices)`
  - Computes the current best bid and ask prices from the maintained active index lists.
- `_orderbook_window_key(base_name, trade_window_seconds)`
  - Returns the versioned key name for one orderbook array, for example `bid_price__w5`.
- `_empty_orderbook_payload(trade_window_seconds, depth)`
  - Returns schema-valid empty orderbook arrays and window metadata for one requested window version.
- `build_orderbook_history(init_rows, update_rows, trade_rows, start_time, depth, trade_window_seconds)`
  - Replays raw orderbook updates against the shared trade/update overlap window.
  - Emits one snapshot for each integer-second `bucket_start` produced from the requested `trade_window_seconds`.
  - Applies only updates with `update_time < bucket_start` to each snapshot.
  - Returns:
    - `time_axis`
    - `bid_price`
    - `bid_size`
    - `ask_price`
    - `ask_size`
    - `bid`
    - `ask`
    - `mid`
- `build_orderbook_payload(context)`
  - Wraps `build_orderbook_history(...)` into the payload dictionary consumed by the pipeline.
  - Writes orderbook keys as `time_axis__wN`, `bid_price__wN`, `bid_size__wN`, `ask_price__wN`, `ask_size__wN`, `bid__wN`, `ask__wN`, and `mid__wN`.
  - Returns empty typed arrays for the requested suffix when there are no trades, no updates, no valid overlap, or no complete buckets.

## `src/preprocess/trade.py`

Builds the trade dataset payload.

### Functions

- `_trade_window_key(base_name, trade_window_seconds)`
  - Returns the versioned key name for one trade array, for example `trade_time__w5`.
- `_empty_trade_payload(trade_window_seconds)`
  - Returns empty typed arrays and trade metadata for one requested window version.
- `_sorted_trade_rows(trade_rows)`
  - Sorts raw trade rows by normalized event time using a stable sort and stores normalized seconds in column 0.
- `_aggregate_trade_rows(rows, bucket_starts, trade_window_seconds)`
  - Aggregates trade volume by `(bucket_start, price, side)` over half-open bucket ranges `[start, start + trade_window_seconds)`.
- `build_trade_payload(context)`
  - Returns the normalized trade payload used by trade-based views.
  - Uses the common trade/update overlap window, trims 1 second from both ends, emits only complete integer-second buckets, and writes keys as `trade_time__wN`, `trade_price__wN`, `trade_volume__wN`, and `trade_side__wN`.
  - Returns empty typed arrays for the requested suffix when there are no trades, no updates, no valid overlap, or no complete buckets.

## `src/preprocess/time_utils.py`

Shared time normalization and bucket-grid helpers.

### Functions

- `normalize_event_seconds(event_seconds)`
  - Normalizes raw seconds across day rollovers.
- `event_seconds_to_datetime64(event_seconds, day_origin)`
  - Converts normalized event seconds into `datetime64[ns]`.
- `sorted_update_times(update_rows)`
  - Returns sorted normalized update event seconds.
- `compute_trimmed_window(anchor_times, update_times)`
  - Intersects the anchor time range and the update time range, then trims 1 second from both ends.
- `iter_bucket_starts(trimmed_start, trimmed_end, window_seconds)`
  - Emits integer-second bucket starts and drops the trailing partial bucket.

## Example

```python
from pathlib import Path

from src.preprocess import preprocess_batch
from src.raw_batches import discover_raw_batches

raw_dir = Path("data/raw")
output_dir = Path("data/preprocessed")
batches = discover_raw_batches(raw_dir)

datasets = preprocess_batch(batches[0], output_dir, depth=10, trade_window_seconds=5)
for dataset in datasets:
    print(dataset.preprocess_type, dataset.path.name, dataset.available_views)
```

## Batch Conversion Entrypoint

`result/convert_data.py` is the script-level entrypoint for converting raw batches from `data/raw` into preprocess artifacts in `data/preprocessed`.

- `PREPROCESS_TRADE_WINDOWS = (1, 5, 10, 30)`
- Each batch is processed once per window value.
- Because preprocess outputs are mergeable, those writes produce one `preprocess-orderbook-*.npz` file and one `preprocess-trade-*.npz` file per raw batch, with multiple `__wN` payload versions inside each file.

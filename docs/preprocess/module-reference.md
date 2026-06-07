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
- `PREPROCESS_TIMEZONE`
  - Time zone used when generating preprocess timestamps for filenames and metadata.

### Data Models

- `PreprocessContext`
  - `batch`
  - `depth`
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

- `generate_preprocess_timestamp()`
  - Returns a timestamp string in `YYYYMMDD.HHMMSS.mmm` format using `PREPROCESS_TIMEZONE`.
- `_validate_depth(depth)`
  - Rejects non-positive or non-integer depth values.
- `build_preprocess_context(batch, depth, loaded_batch=None)`
  - Loads a raw batch and normalizes it into a `PreprocessContext`.
- `_save_preprocess_payload(...)`
  - Writes payload data and metadata into a compressed `.npz` file and rediscovers the written artifact.
- `preprocess_batch(batch, output_dir, depth=DEFAULT_DEPTH, builder_registry=None, preprocess_timestamp=None, seq_num=0)`
  - Runs every registered preprocess builder for a single raw batch.
- `preprocess_batches(batches, output_dir, depth=DEFAULT_DEPTH, builder_registry=None, progress_callback=None)`
  - Processes multiple raw batches and reports progress if requested.

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

## `src/preprocess/orderbook.py`

Builds the orderbook dataset payload.

### Functions

- `update_orderbook(orderbook, price_levels, price, volume, side)`
  - Applies one level update into the in-memory book representation.
- `get_bid_ask(orderbook, price_levels)`
  - Computes the current best bid and ask prices from the signed orderbook array.
- `_visible_depth_indices(orderbook, depth)`
  - Selects the currently visible bid and ask levels to keep in the output payload.
- `build_orderbook_history(init_rows, update_rows, start_time, depth)`
  - Replays raw orderbook updates and returns:
    - `price_axis`
    - `time_axis`
    - `data`
    - `bid`
    - `ask`
    - `mid`
- `build_orderbook_payload(context)`
  - Wraps `build_orderbook_history(...)` into the payload dictionary consumed by the pipeline.

### Output Keys

The current orderbook payload includes:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

Only the first five keys are currently required by the pipeline contract. `mid` is an additional convenience array.

## `src/preprocess/trade.py`

Builds the trade dataset payload.

### Functions

- `_empty_trade_payload()`
  - Returns empty typed arrays when a batch has no trades.
- `_sorted_trade_rows(trade_rows)`
  - Sorts raw trade rows by event time using a stable sort.
- `build_trade_payload(context)`
  - Returns the normalized trade payload used by trade-based views, or empty typed arrays when the batch has no trades.

### Output Keys

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

## `src/preprocess/exceptions.py`

- `PreprocessError`
  - Base runtime error for preprocess failures.
- `PreprocessValidationError`
  - Raised when preprocess input arguments are invalid.

## Example

```python
from pathlib import Path

from src.preprocess import preprocess_batch
from src.raw_batches import discover_raw_batches

raw_dir = Path("data/v3")
output_dir = Path("data/preprocessed")
batches = discover_raw_batches(raw_dir)

datasets = preprocess_batch(batches[0], output_dir, depth=10)
for dataset in datasets:
    print(dataset.preprocess_type, dataset.path.name, dataset.available_views)
```

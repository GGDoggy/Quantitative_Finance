# Preprocess Module Reference

## `service.py`

- `build_context(batch, time_step)`
  - uses `src.raw_batches.load_raw_batch()` to build `PreprocessContext`
- `preprocess_batch(...)`
  - runs registered preprocess builders
  - merges payload chunks
  - writes one preprocessed artifact
- `preprocess_batches(...)`
  - wraps `preprocess_batch()` for multiple batches

## `builders/orderbook.py`

Produces:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

## `builders/trades.py`

Produces:

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

## `registry.py`

- `PLOT_REGISTRY`
  - `orderbook`
  - `trades_scatter`
  - `trade_volume_timeline`

The registry is maintained inside `src.preprocess`.

## `datasets.py`

Keeps two categories of behavior:

- compatibility wrappers
  - `discover_raw_batches(...)`
  - `discover_preprocessed_datasets(...)`
  - `find_simulation_files(...)`
- payload loading and validation
  - `load_preprocessed_payload(...)`

Artifact discovery and naming rules now come from:

- `src.raw_batches`
- `src.dataset_artifacts`

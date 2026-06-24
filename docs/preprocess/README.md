# `src.preprocess`

`src.preprocess` converts a `RawBatch` from `src.raw_batches` into one or more preprocessed `.npz` datasets.

- [formats-and-contracts.md](formats-and-contracts.md)
- [module-reference.md](module-reference.md)

## Scope

- `src/preprocess/__init__.py`
  - Re-exports the supported preprocess API surface.
- `src/preprocess/pipeline.py`
  - Orchestrates batch loading, builder execution, metadata injection, and `.npz` writes.
- `src/preprocess/orderbook.py`
  - Builds trade-window-aligned orderbook history arrays from raw level2 snapshots and updates.
- `src/preprocess/trade.py`
  - Builds fixed-window trade aggregates from raw trade rows and merges multiple window versions into one trade `.npz`.
- `src/preprocess/exceptions.py`
  - Defines preprocess-specific exception types.

## Data Flow

```text
RawBatch
  -> load_raw_batch()
  -> build_preprocess_context()
  -> PreprocessContext
  -> PLOT_REGISTRY builders
  -> payload dictionaries
  -> preprocess-{type}-{timestamp}.npz
  -> src.dataset_artifacts.discover_preprocessed_artifacts()
```

The library pipeline writes one artifact per registered preprocess type for each raw batch. By default the filename suffix is the raw batch timestamp from the CSV filenames, so one raw batch yields one `orderbook` artifact and one `trade` artifact that share the same `preprocess_timestamp`.

Both preprocess artifacts are append-friendly for windowed payloads: rerunning `preprocess_batch(..., trade_window_seconds=N)` for the same `preprocess_timestamp` preserves existing `*__wM` payloads for other `M` values and overwrites only the matching `N` version.

## Current Outputs

The preprocess pipeline currently writes two dataset types:

- `orderbook`
  - Provides the `orderbook` view.
  - Stores versioned orderbook snapshots keyed by window suffix, for example `time_axis__w5` and `bid_price__w5`.
- `trade`
  - Provides the `trades_scatter` and `trade_volume_timeline` views.
  - Stores versioned trade aggregates keyed by window suffix, for example `trade_time__w5` and `trade_volume__w5`.

`result/convert_data.py` is the batch conversion entrypoint for `data/raw`; it writes window versions for `trade_window_seconds` values `(1, 5, 10, 30)`.

## Implementation Notes

- `src.preprocess.orderbook.build_orderbook_history(...)` now tracks active bid and ask indices incrementally instead of scanning the full signed book array after every update.
- The orderbook builder now uses the same trimmed overlap window as the trade builder and writes only suffixed keys such as `time_axis__w5`, `bid_price__w5`, and `mid__w5`.
- Each orderbook row is anchored to one `bucket_start` from the shared trade/update grid.
- For one bucket, the builder applies every level2 update with `update_time < bucket_start` and excludes updates at exactly `bucket_start`.
- Each emitted depth row remains fixed-width:
  - `bid_price__wN`, `bid_size__wN`, `ask_price__wN`, `ask_size__wN`
- This keeps orderbook and trade payloads aligned on the same integer-second bucket grid without allocating a dense `updates x active_prices` matrix.
- Empty-but-valid payloads are written when there are no trades, no updates, no valid overlap, or no complete bucket after trimming.

## Public API

- `DEFAULT_DEPTH`
- `PLOT_REGISTRY`
- `PreprocessContext`
- `PreprocessBuilderSpec`
- `preprocess_batch(...)`
- `preprocess_batches(...)`
- `PreprocessError`
- `PreprocessValidationError`

Both `preprocess_batch(...)` and `preprocess_batches(...)` accept `trade_window_seconds`, a positive integer that controls the shared trade and orderbook bucket size in seconds.

## Relationships

- `src.raw_batches`
  - Supplies `RawBatch`, `LoadedRawBatch`, discovery, and CSV loading.
- `src.dataset_artifacts`
  - Owns preprocess file naming, metadata parsing, and artifact discovery.

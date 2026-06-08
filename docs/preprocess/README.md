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
  - Builds orderbook history arrays from raw level2 snapshots and updates.
- `src/preprocess/trade.py`
  - Builds trade arrays from raw trade rows.
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
  -> preprocess-{type}-{timestamp}-{seq}.npz
  -> src.dataset_artifacts.discover_preprocessed_artifacts()
```

The library pipeline normally writes one artifact per registered preprocess type. A separate repository utility, `result/convert_data.py`, may emit multiple `orderbook` artifacts for the same raw batch when it falls back to chunked conversion after `MemoryError`.

## Current Outputs

The preprocess pipeline currently writes two dataset types:

- `orderbook`
  - Provides the `orderbook` view.
- `trade`
  - Provides the `trades_scatter` and `trade_volume_timeline` views.

## Implementation Notes

- `src.preprocess.orderbook.build_orderbook_history(...)` now tracks active bid and ask indices incrementally instead of scanning the full signed book array after every update.
- The orderbook builder stores only the visible depth rows needed for the final output matrix, avoiding one full orderbook snapshot copy per update.

## Public API

- `DEFAULT_DEPTH`
- `PLOT_REGISTRY`
- `PreprocessContext`
- `PreprocessBuilderSpec`
- `preprocess_batch(...)`
- `preprocess_batches(...)`
- `PreprocessError`
- `PreprocessValidationError`

## Relationships

- `src.raw_batches`
  - Supplies `RawBatch`, `LoadedRawBatch`, discovery, and CSV loading.
- `src.dataset_artifacts`
  - Owns preprocess file naming, metadata parsing, and artifact discovery.

# `src.raw_batches`

`src.raw_batches` handles parsing, discovery, and loading for `data/raw` CSV batches.

`data/raw` is the only raw data directory in the current repository layout.

## Responsibilities

- group `init`, `updates`, and `trade` CSV files into one `RawBatch`
- parse filename timestamps into `datetime` and unix seconds
- load CSV rows into a `LoadedRawBatch`

## Filename Format

```text
level2-{product_id}-init-{timestamp}.csv
level2-{product_id}-updates-{timestamp}.csv
trade-{product_id}-{timestamp}.csv
```

`discover_raw_batches()` groups files by `(product_id, timestamp)` and returns sorted `RawBatch` objects.

## Public API

- `parse_timestamp(timestamp: str) -> datetime`
- `file_time_to_unix(file_time: str) -> int`
- `parse_raw_filename(filename: str) -> RawFilenameMetadata | None`
- `discover_raw_batches(raw_dir: Path | str) -> list[RawBatch]`
- `load_raw_batch(batch: RawBatch) -> LoadedRawBatch`

## Main Models

### `RawBatch`

- `product_id`
- `timestamp`
- `init_path`
- `updates_path`
- `trade_path`
- `is_preprocessed`

### `LoadedRawBatch`

- `init: list[list[float]]`
- `updates: list[list[float]]`
- `trades: list[list[float]]`
- `start_time: float`

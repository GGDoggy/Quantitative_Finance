# Analyze Module Reference

## `src/analyze/__init__.py`

Public re-export surface for analysis execution:

- `AnalyzeJobResult`
- `AnalyzeRequest`
- `AnalyzeResult`
- `LoadedAnalyzeData`
- `RawBatch`
- `DATA_V3_PATH`
- `OUTPUT_PATH`
- `parse_dataset_groups(...)`
- `load_raw_dataset(...)`
- `analyze_loaded_data(...)`
- `analyze_batch(...)`
- `analyze_batches(...)`
- `build_output_path(...)`
- `generate_analyze_timestamp()`

## `src/analyze/models.py`

Defines the data contracts that move through the analysis pipeline.

### Data Models

- `LoadedAnalyzeData`
  - `init`
  - `updates`
  - `trades`
  - `start_time`
- `AnalyzeRequest`
  - `analysis_name`
- `AnalyzeResult`
  - `price`
  - `vol`
  - `time`
  - `side`
  - `penetrated`
  - `spread`
  - `opp_vol`
  - `fill_rate`
- `AnalyzeJobResult`
  - `dataset`
  - `output_path`
  - `overwritten`
  - `seq_num`
- `AnalyzeWorkerPayload`
  - Internal process-worker return payload used by batch parallel execution.

### Methods

- `AnalyzeRequest.__post_init__()`
  - Rejects empty `analysis_name` values.
- `AnalyzeResult.as_tuple()`
  - Returns the result arrays in the saved `.npz` field order.
- `AnalyzeWorkerPayload.to_job_result(dataset)`
  - Reconstructs a public `AnalyzeJobResult` from worker output.

## `src/analyze/core.py`

Owns the fill-rate analysis algorithm for one loaded batch.

### Internal Models

- `_IntervalContext`
  - Snapshot of best prices, best sizes, and book state at the start of one update interval.

### Functions

- `_sorted_rows(rows)`
  - Sorts raw rows by event time.
- `_apply_level_update(levels, price, volume)`
  - Upserts or removes a price level based on the updated visible size.
- `_initialize_book(init_rows)`
  - Builds the initial bid and ask maps from the raw snapshot rows.
- `_best_bid(levels)`
  - Returns the highest visible bid price and its size.
- `_best_ask(levels)`
  - Returns the lowest visible ask price and its size.
- `_spread(best_bid_price, best_ask_price)`
  - Returns the visible bid-ask spread or `NaN` when one side is missing.
- `_side_name(trade_side)`
  - Maps the raw trade side integer to `"bid"` or `"ask"`.
- `_price_sort_key(side, price)`
  - Sorts bid-side grouped prices descending and ask-side grouped prices ascending.
- `_is_better_than_last(side, price, last_price)`
  - Detects whether a grouped trade price is better than the last traded price seen in the same interval and side.
- `_starting_volume(context, side, price)`
  - Returns the visible size at a traded level at interval start.
- `_fill_rate(penetrated, traded_volume, starting_volume)`
  - Computes fill rate as `1.0`, `traded_volume / starting_volume`, or `NaN`.
- `_build_interval_context(update_row, bid_levels, ask_levels)`
  - Captures the interval-start orderbook state after applying the current update row.
- `analyze_loaded_data(data)`
  - Scans adjacent update intervals, groups trades by side and price inside each interval, and returns the normalized analysis arrays.

### Behavior Notes

- The algorithm applies each current update row before analyzing the interval until the next update row.
- Intervals without trades do not produce output rows.
- If fewer than two updates exist, or if no trades exist, the function returns empty typed arrays.
- Grouping is per interval, per side, and per traded price.
- `penetrated=True` means the interval later traded at a better price than the current grouped level on the same side.

## `src/analyze/service.py`

Orchestrates loading, persistence, and multi-batch execution.

### Constants

- `DATA_V3_PATH`
  - Default raw batch directory.
- `OUTPUT_PATH`
  - Default analyze artifact directory.
- `ANALYZE_RESULT_KEYS`
  - Saved `.npz` field order for `AnalyzeResult`.
- `ANALYZE_TIMEZONE`
  - Time zone used for generated analyze timestamps.

### Functions

- `generate_analyze_timestamp()`
  - Returns a `YYYYMMDD.HHMMSS.mmm` timestamp in `Asia/Taipei`.
- `build_output_path(output_path, analysis_name, analyze_timestamp, seq_num)`
  - Builds a validated analyze artifact path through `src.dataset_artifacts`.
- `parse_dataset_groups(data_v3_path)`
  - Discovers raw batches from a directory.
- `load_raw_dataset(dataset)`
  - Loads one `RawBatch` into `LoadedAnalyzeData`.
- `serialize_result_for_npz(result)`
  - Maps an `AnalyzeResult` into a save-ready dictionary.
- `save_result_file(output_file, ..., dataset, result)`
  - Writes metadata and result arrays into a compressed `.npz` file.
- `analyze_loaded_dataset(data, request)`
  - Dispatches the current request type to the core algorithm.
- `analyze_batch(dataset, request, output_dir)`
  - Runs one analysis job and writes a single output artifact with `seq_num=0`.
- `get_default_worker_count(task_count)`
  - Caps worker count to the available CPU count and task count.
- `_process_dataset_job(dataset, output_path, request, analyze_timestamp, seq_num)`
  - Worker entry point for parallel multi-batch execution.
- `_run_datasets_in_parallel(selected, output_path, request)`
  - Runs multiple datasets in a shared `ProcessPoolExecutor`.
- `analyze_batches(datasets, request, output_dir)`
  - Uses serial execution for zero or one dataset, otherwise runs jobs in parallel and restores input ordering.

### Persistence Contract

Saved analyze artifacts use this filename format:

```text
analyze-{analysis_name}-{analyze_timestamp}-{seq_num}.npz
```

Current required metadata fields:

- `analysis_name`
- `analyze_timestamp`
- `seq_num`
- `product_id`
- `timestamp`
- `file_stem`

Current result array fields:

- `price`
- `vol`
- `time`
- `side`
- `penetrated`
- `spread`
- `opp_vol`
- `fill_rate`

## Example

```python
from pathlib import Path

from src.analyze import AnalyzeRequest, analyze_batch, parse_dataset_groups

raw_dir = Path("data/v3")
output_dir = Path("data/preprocessed")
batches = parse_dataset_groups(raw_dir)
request = AnalyzeRequest(analysis_name="fill_rate")

job = analyze_batch(batches[0], request, output_dir)
print(job.output_path.name, job.seq_num, job.overwritten)
```

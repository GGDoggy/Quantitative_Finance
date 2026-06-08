# `src.analyze`

`src.analyze` loads raw `data/v3` batches, runs trade fill-rate analysis, and writes compressed `.npz` artifacts into `data/preprocessed`.

- [module-reference.md](module-reference.md)

## Scope

- `src/analyze/__init__.py`
  - Re-exports the supported analysis API surface.
- `src/analyze/models.py`
  - Defines request, loaded-input, in-memory result, and job result models.
- `src/analyze/core.py`
  - Implements the fill-rate analysis algorithm on one loaded raw batch.
- `src/analyze/service.py`
  - Orchestrates raw batch loading, timestamp generation, output naming, single-batch execution, batch-parallel execution, and `.npz` writes.

## Data Flow

```text
RawBatch
  -> load_raw_dataset()
  -> LoadedAnalyzeData
  -> analyze_loaded_data()
  -> AnalyzeResult
  -> save_result_file()
  -> analyze-{analysis_name}-{analyze_timestamp}-{seq_num}.npz
  -> src.dataset_artifacts.discover_analyze_artifacts()
```

## Current Analysis

The current implementation supports one analysis request:

- `fill_rate`
  - Aggregates trade volume between adjacent orderbook updates.
  - Evaluates that traded volume against the visible starting size at each traded price level.
  - Marks a row as fully filled when the interval traded through a better price than the traded level.

## Quick Example

```python
from pathlib import Path

from src.analyze import AnalyzeRequest, analyze_batch, parse_dataset_groups

raw_dir = Path("data/v3")
output_dir = Path("data/preprocessed")
batches = parse_dataset_groups(raw_dir)
request = AnalyzeRequest(analysis_name="fill_rate")

job = analyze_batch(batches[0], request, output_dir)
print(job.output_path)
```

## Result Columns

Each saved analyze artifact currently contains these analysis arrays:

- `price`
  - Price level of the grouped trades.
- `vol`
  - Total traded volume at that price within one update interval.
- `time`
  - Interval start timestamp, taken from the current update row.
- `side`
  - `"bid"` or `"ask"` for the traded book side.
- `penetrated`
  - `True` when the interval traded through a better price on that side.
- `spread`
  - Best ask minus best bid at the interval start.
- `opp_vol`
  - Visible top-of-book size on the opposite side at the interval start.
- `fill_rate`
  - `1.0` for penetrated levels, otherwise `traded_volume / starting_volume` when a starting level existed, or `NaN` when no starting size existed.

## Output Metadata

Saved `.npz` artifacts also include:

- `analysis_name`
- `analyze_timestamp`
- `seq_num`
- `product_id`
- `timestamp`
- `file_stem`

## Public API

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

## Relationships

- `src.raw_batches`
  - Supplies `RawBatch`, `LoadedRawBatch`, raw batch discovery, and CSV loading.
- `src.dataset_artifacts`
  - Owns analyze filename validation, path construction, and artifact discovery.
- `data/v3`
  - Provides the raw level2 and trade CSV inputs consumed by analysis.
- `data/preprocessed`
  - Receives the persisted analyze `.npz` artifacts.

## Current Limitations

- `AnalyzeRequest.analysis_name` is currently validated but only `fill_rate` is implemented.
- Output rows are generated only for intervals that contain trades and have a following update boundary.
- Generated artifact timestamps use `Asia/Taipei`, while raw dataset timestamps come from batch metadata.

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
- `AnalyzeWorkerPayload`
  - Internal process-worker return payload used by batch parallel execution.

### Methods

- `AnalyzeRequest.__post_init__()`
  - Rejects empty `analysis_name` values.
- `AnalyzeResult.as_tuple()`
  - Returns the result arrays in the saved `.npz` field order.
- `AnalyzeWorkerPayload.to_job_result(dataset)`
  - Reconstructs a public `AnalyzeJobResult` from worker output.

## `src/analyze/service.py`

Orchestrates loading, persistence, and multi-batch execution.

### Constants

- `DATA_V3_PATH`
  - Default raw batch directory.
- `OUTPUT_PATH`
  - Default analyze artifact directory.
- `ANALYZE_RESULT_KEYS`
  - Saved `.npz` field order for `AnalyzeResult`.

### Functions

- `build_output_path(output_path, analysis_name, analyze_timestamp)`
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
- `analyze_batch(dataset, request, output_dir, analyze_timestamp=None)`
  - Runs one analysis job and writes a single output artifact.
  - Defaults `analyze_timestamp` to `dataset.timestamp`.
- `_process_dataset_job(dataset, output_path, request, analyze_timestamp)`
  - Worker entry point for parallel multi-batch execution.
- `_run_datasets_in_parallel(selected, output_path, request, analyze_timestamp=None)`
  - Runs multiple datasets in a shared `ProcessPoolExecutor`.
  - Uses each dataset's `timestamp` unless the caller explicitly overrides `analyze_timestamp`.
- `analyze_batches(datasets, request, output_dir, analyze_timestamp=None)`
  - Uses serial execution for zero or one dataset, otherwise runs jobs in parallel and restores input ordering.

### Persistence Contract

Saved analyze artifacts use this filename format:

```text
analyze-{analysis_name}-{analyze_timestamp}.npz
```

Current required metadata fields:

- `analysis_name`
- `analyze_timestamp`
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
print(job.output_path.name, job.overwritten)
```

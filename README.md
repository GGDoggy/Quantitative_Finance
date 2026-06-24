# Quantitative Finance Project

This repository is a quantitative finance research project built around Coinbase market data. The active documentation focus is raw batch ingestion and windowed preprocess artifact generation.

## Current Pipeline

```text
data/raw/*.csv
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/preprocess-*.npz
  -> src.dataset_artifacts discovery / downstream visualization

data/raw/*.csv
  -> result/convert_data.py
  -> src.preprocess.preprocess_batch()
  -> data/preprocessed/preprocess-*.npz
```

## Project Layout

- `server/`
  - Coinbase websocket collector and config.
- `src/raw_batches/`
  - Raw CSV filename parsing, batch discovery, and loading.
- `src/preprocess/`
  - Raw batch to windowed preprocessed `.npz` pipeline.
- `src/dataset_artifacts/`
  - Preprocess artifact naming, parsing, and discovery.
- `docs/`
  - Module documentation and contracts.
- `result/`
  - Conversion scripts and research notebooks. `result/convert_data.py` preprocesses `data/raw` batches for multiple trade windows.
- `test/`
  - Automated tests.

## Installation

```bash
conda activate quantitative_finance
pip install -r requirements.txt
```

For one-off commands, prefer `conda run -n quantitative_finance ...` so the project interpreter is explicit.

## Raw Data Collection

Run `server/websocket.py` with `server/` as the working directory. The collector writes output files into the current working directory.

Important constraints:

- only one `product_id` is supported at a time
- generated filename timestamps are UTC
- the execution directory determines where `level2-*.csv` and `trade-*.csv` are written

## Public APIs

### `src.raw_batches`

- `discover_raw_batches(raw_dir)`
- `load_raw_batch(batch)`
- `parse_raw_filename(filename)`
- `parse_timestamp(timestamp)`
- `file_time_to_unix(file_time)`

### `src.preprocess`

- `DEFAULT_DEPTH`
- `PLOT_REGISTRY`
- `PreprocessContext`
- `PreprocessBuilderSpec`
- `preprocess_batch(...)`
- `preprocess_batches(...)`

`preprocess_batch(..., trade_window_seconds=N)` writes one orderbook artifact and one trade artifact for the selected raw batch. Re-running the same `preprocess_timestamp` with a different `N` appends a new `__wN` payload version to the same preprocess files; re-running the same `N` overwrites only that version.

### `src.dataset_artifacts`

- `build_preprocessed_output_path(...)`
- `parse_preprocessed_filename(...)`
- `discover_preprocessed_artifacts(...)`
- `detect_available_views(...)`

## Artifact Formats

Preprocess outputs:

```text
data/preprocessed/preprocess-{preprocess_type}-{preprocess_timestamp}.npz
```

Current preprocess types are:

- `orderbook`
  - Windowed keys such as `time_axis__w5`, `bid_price__w5`, `bid_size__w5`, `ask_price__w5`, `ask_size__w5`, `bid__w5`, `ask__w5`, and `mid__w5`.
- `trade`
  - Windowed keys such as `trade_time__w5`, `trade_price__w5`, `trade_volume__w5`, and `trade_side__w5`.

## Documentation

- [docs/README.md](docs/README.md)
- [docs/raw_batches/README.md](docs/raw_batches/README.md)
- [docs/preprocess/README.md](docs/preprocess/README.md)
- [docs/preprocess/formats-and-contracts.md](docs/preprocess/formats-and-contracts.md)
- [docs/dataset_artifacts/README.md](docs/dataset_artifacts/README.md)

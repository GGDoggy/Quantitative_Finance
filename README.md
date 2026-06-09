# Quantitative Finance Project

This repository is a quantitative finance research project built around Coinbase market data. The active codebase is organized around raw batch ingestion, preprocess artifact generation, and trade fill-rate analysis.

## Current Pipeline

```text
data/v3/*.csv
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/preprocess-*.npz
  -> downstream discovery / visualization

data/v3/*.csv
  -> src.raw_batches
  -> src.analyze
  -> data/preprocessed/analyze-*.npz
```

## Project Layout

- `server/`
  - Coinbase websocket collector and config.
- `src/raw_batches/`
  - Raw CSV filename parsing, batch discovery, and loading.
- `src/preprocess/`
  - Raw batch to preprocessed `.npz` pipeline.
- `src/dataset_artifacts/`
  - Preprocess and analyze artifact naming, parsing, and discovery.
- `src/analyze/`
  - Trade fill-rate analysis pipeline and artifact writing.
- `docs/`
  - Module documentation and contracts.
- `test/`
  - Automated tests.

## Installation

```bash
pip install -r requirements.txt
```

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

### `src.dataset_artifacts`

- `build_preprocessed_output_path(...)`
- `build_analyze_output_path(...)`
- `parse_preprocessed_filename(...)`
- `parse_analyze_filename(...)`
- `discover_preprocessed_artifacts(...)`
- `discover_analyze_artifacts(...)`
- `detect_available_views(...)`

### `src.analyze`

- `analyze_loaded_data(...)`
- `analyze_batch(dataset, request, output_dir)`
- `analyze_batches(datasets, request, output_dir)`
- `build_output_path(...)`

## Artifact Formats

Preprocess outputs:

```text
data/preprocessed/preprocess-{preprocess_type}-{preprocess_timestamp}.npz
```

Analyze outputs:

```text
data/preprocessed/analyze-{analysis_name}-{analyze_timestamp}.npz
```

## Documentation

- [docs/README.md](docs/README.md)
- [docs/raw_batches/README.md](docs/raw_batches/README.md)
- [docs/preprocess/README.md](docs/preprocess/README.md)
- [docs/dataset_artifacts/README.md](docs/dataset_artifacts/README.md)

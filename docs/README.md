# Docs

This directory contains module-level documentation for the active codebase.

## Index

1. [raw_batches/README.md](raw_batches/README.md)
   Raw CSV naming, batch discovery, and loading.
2. [preprocess/README.md](preprocess/README.md)
   Raw batch to preprocess artifact pipeline.
3. [analyze/README.md](analyze/README.md)
   Raw batch to analyze artifact pipeline.
4. [dataset_artifacts/README.md](dataset_artifacts/README.md)
   Artifact naming, parsing, and discovery for preprocess and analyze outputs.

## Current Data Flow

```text
data/v3/*.csv
  -> src.raw_batches.discover_raw_batches()
  -> src.preprocess.preprocess_batch()
  -> data/preprocessed/preprocess-*.npz

data/v3/*.csv
  -> src.raw_batches.discover_raw_batches()
  -> src.analyze.analyze_batch()
  -> data/preprocessed/analyze-*.npz

data/temp/*.csv
  -> result/convert_data.py
  -> src.preprocess.pipeline internal helpers
  -> src.analyze.analyze_batch()
  -> data/preprocessed/preprocess-*.npz
  -> data/preprocessed/analyze-*.npz
```

## Active Packages

- `src.raw_batches`
  - Raw CSV parsing, timestamp helpers, discovery, and loading.
- `src.preprocess`
  - Preprocess payload builders and `.npz` writing.
- `src.dataset_artifacts`
  - Artifact filename rules, metadata parsing, and discovery.
- `src.analyze`
  - Analysis request models, execution, and artifact writing.

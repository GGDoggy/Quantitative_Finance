# Docs

This directory contains module-level documentation for the active Coinbase market data codebase. The current docs focus on raw batch ingestion, preprocessing, and preprocess artifact discovery.

## Index

1. [raw_batches/README.md](raw_batches/README.md)
   Raw CSV naming, batch discovery, and loading.
2. [preprocess/README.md](preprocess/README.md)
   Raw batch to windowed preprocess artifact pipeline.
3. [dataset_artifacts/README.md](dataset_artifacts/README.md)
   Artifact naming, parsing, and discovery for preprocess outputs.

## Current Data Flow

```text
data/raw/*.csv
  -> src.raw_batches.discover_raw_batches()
  -> src.preprocess.preprocess_batch(trade_window_seconds=N)
  -> data/preprocessed/preprocess-*.npz

data/raw/*.csv
  -> result/convert_data.py
  -> src.preprocess.preprocess_batch(trade_window_seconds in 1,5,10,30)
  -> data/preprocessed/preprocess-*.npz
```

## Active Packages

- `src.raw_batches`
  - Raw CSV parsing, timestamp helpers, discovery, and loading.
- `src.preprocess`
  - Windowed orderbook/trade payload builders and `.npz` writing.
- `src.dataset_artifacts`
  - Artifact filename rules, metadata parsing, and discovery.

## Current Artifact Families

- `preprocess-orderbook-{timestamp}.npz`
  - Stores orderbook snapshots under versioned `*__wN` keys, one version per `trade_window_seconds` value.
- `preprocess-trade-{timestamp}.npz`
  - Stores fixed-window trade aggregates under versioned `trade_*__wN` keys.

See [preprocess/formats-and-contracts.md](preprocess/formats-and-contracts.md) for payload keys and [dataset_artifacts/README.md](dataset_artifacts/README.md) for discovery rules.

# Quantitative Finance Project

Coinbase market-data collection, visualization, and simulation experiments.


## Main Components

- `server/websocket.py`
  - Subscribes to `heartbeats`, `level2`, and `market_trades`.
  - Checks `sequence_num` and heartbeat continuity.
  - Writes `level2-*.csv` and `trade-*.csv` in the current working directory.
- `gui/`
  - Panel dashboard package split by responsibility: app bootstrap, dashboard composition, catalog logic, rendering, layout, simulation controls, and event handlers.
  - Supports `Orderbook`, `Trades Scatter`, `Trade Volume Timeline`, and `Fill Probability`.
- `webUI.py`
  - Primary dashboard entry point that serves the refactored `gui` package.
- `src/preprocess/`
  - Shared non-UI preprocessing and dataset catalog logic.
- `src/plots/`
  - Non-UI plot builders and plot registry definitions.
- `src/simulation/`
  - Fill-probability simulation utilities and algorithms.
- `test/`
  - Small scripts for legacy plotting and simulation experiments.

## Notes

- `server/websocket.py` only supports one product at a time.
- Timestamps in generated filenames are UTC.
- `webUI.py` serves the local Panel app with `show=True`.
- No standalone preprocess CLI entry point is currently provided.

## Data Layout

### v1

Snapshot-only JSON format. One file can contain multiple products.

```json
{
  "PRODUCT_ID": {
    "bid": { "PRICE": "AMOUNT" },
    "offer": { "PRICE": "AMOUNT" }
  }
}
```

### v2

JSON event format for multiple products.

`level2`:

```json
{
  "PRODUCT_ID": {
    "TIME": {
      "type": "snapshot or update",
      "data": {
        "bid": { "PRICE": "AMOUNT" },
        "offer": { "PRICE": "AMOUNT" }
      }
    }
  }
}
```

`trade`:

```json
{
  "PRODUCT_ID": {
    "TIME": {
      "BUY": { "PRICE": 0.0 },
      "SELL": { "PRICE": 0.0 }
    }
  }
}
```

### v3

Single-product CSV format used by the current pipeline.

Level 2 batch:

- `level2-PRODUCT_ID-init-yyyymmdd.hhmmss.csv`
- `level2-PRODUCT_ID-updates-yyyymmdd.hhmmss.csv`

Trade batch:

- `trade-PRODUCT_ID-yyyymmdd.hhmmss.csv`

`init` columns:

| Price | Volume | Side |
| - | - | - |

`updates` columns:

| Time | Price | Volume | Side |
| - | - | - | - |

`trade` columns:

| Time | Price | Volume | Side |
| - | - | - | - |

- In `level2`, `Side` is `-1` for sell and `+1` for buy.
- In `trade`, `Side` is `-1` for sell maker and `+1` for buy maker.
- `Time` is measured in seconds from midnight of the filename date.

## Preprocess API Boundaries

`src.preprocess` now has an explicit package-level **public API** for stable imports.

### Stable public API (import from `src.preprocess`)

- Exceptions: `PreprocessError`, `PreprocessValidationError`, `PreprocessOutputConflictError`, `PreprocessedDataError`, `PreprocessedDataFileError`, `PreprocessedDataSchemaError`
- Catalog/data models: `RawBatch`, `PreprocessedDataset`, `PlotDatasetLocator`
- Catalog entry points: `discover_raw_batches`, `discover_preprocessed_datasets`, `load_preprocessed_payload`
- Preprocess services: `DEFAULT_TIME_STEP`, `preprocess_batch`, `preprocess_batches`

### Internal modules (import explicitly, no stability guarantee)

- `src.preprocess.catalog` internals and filename/token helpers (for example: simulation filename matching, timestamp/time-step formatting helpers)
- `src.preprocess.common` context construction details
- Plot-specific preprocess builders under `src.preprocess.orderbook`, `src.preprocess.trades_scatter`, and `src.preprocess.trade_volume_timeline`
- Adapters under `src.preprocess.adapters`

### Migration and deprecation rule

- New code should prefer the stable package-level API above.
- If a caller needs an internal helper, import from the concrete internal module directly and treat it as refactorable.
- Some legacy package-level names are currently kept as transitional aliases and emit `DeprecationWarning`; these aliases will be removed in a future cleanup.

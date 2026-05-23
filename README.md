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
  - Fill-probability simulation library module for loading raw datasets and running batch simulations.
- `test/`
  - Small plotting and library-level validation helpers.

## Notes

- `server/websocket.py` only supports one product at a time.
- Timestamps in generated filenames are UTC.
- `webUI.py` serves the local Panel app with `show=True`.
- No standalone preprocess CLI entry point is currently provided.


## Simulation Module

`src.simulation` is a library-only module. It does not provide CLI wrappers,
interactive entrypoints, or GUI adapters.

- Public entry points:
  - `RawSimulationDataset`
  - `LoadedMarketData`
  - `SimulationRequest`
  - `SimulationResult`
  - `SimulationJobResult`
  - `list_algorithms()`
  - `load_raw_dataset()`
  - `simulate_loaded_data()`
  - `simulate_batch()`
  - `simulate_batches()`
- Internal implementation modules:
  - `models.py`: typed request/result containers
  - `registry.py`: algorithm lookup
  - `io.py`: raw CSV discovery/loading and `.npz` serialization
  - `runner.py`: orchestration and parallel execution

Recommended setup for repo-local imports:

```bash
pip install -e .
```

Example preferred usage:

```python
from src.simulation import SimulationRequest, list_algorithms, simulate_batch
```

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

- Models: `RawBatch`, `PreprocessedDataset`, `PlotDatasetLocator`, `PreprocessContext`
- Catalog: `discover_raw_batches`, `discover_preprocessed_datasets`, `find_simulation_files`, `has_simulation_file`
- Filenames: `format_time_step`, `parse_timestamp`
- I/O and services: `load_preprocessed_payload`, `DEFAULT_TIME_STEP`, `preprocess_batch`, `preprocess_batches`
- Exceptions: `PreprocessError`, `PreprocessValidationError`, `PreprocessOutputConflictError`, `PreprocessedDataError`, `PreprocessedDataFileError`, `PreprocessedDataSchemaError`

### Internal modules (import explicitly, no stability guarantee)

- `src.preprocess.models`: preprocess domain models and context types
- `src.preprocess.filenames`: raw/preprocessed/simulation filename parsing and token helpers
- `src.preprocess.io`: CSV/NPZ I/O, schema validation, and preprocess context construction
- `src.preprocess.catalog`: dataset discovery, aggregation, and simulation-file matching
- `src.preprocess.service`: preprocess orchestration over the builder registry
- `src.preprocess.common`: internal transitional re-export facade only
- `src.preprocess.orderbook`, `src.preprocess.trades_scatter`, `src.preprocess.trade_volume_timeline`: plot-specific preprocess builders
- `src.preprocess.adapters`: internal adapters such as registry-backed view detection

### Migration and deprecation rule

- New code should prefer the stable package-level API above.
- GUI, simulation orchestration, dashboard code, and API-surface tests should import stable names from `src.preprocess` unless they explicitly need an internal helper.
- Internal preprocess modules may import shared types from `src.preprocess.models`.
- Do not add new external imports from `src.preprocess.catalog.RawBatch`, `src.preprocess.catalog.PreprocessedDataset`, `src.preprocess.catalog.PlotDatasetLocator`, or `src.preprocess.common.PreprocessContext`; those paths remain only as compatibility aliases.
- If a caller needs an internal helper, import from the concrete internal module directly and treat it as refactorable.

### Test command

- PowerShell: ``$env:PYTHONPATH='.'; pytest test/test_preprocess_public_api.py test/test_preprocess_models_api.py test/test_preprocess_filenames.py test/test_preprocess_io.py test/test_preprocess_catalog_simulation_matching.py test/test_preprocess_catalog_view_detector.py test/test_preprocess_service_registry.py test/test_preprocess_discovery.py``

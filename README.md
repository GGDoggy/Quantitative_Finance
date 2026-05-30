# Quantitative Finance Project

This repository is a quantitative finance research project built around Coinbase market data. The current mainline workflow is no longer a collection of standalone scripts. It is organized into four connected stages:

1. `server/websocket.py`
   Subscribes to `heartbeats`, `level2`, and `market_trades`, and writes raw CSV batches in the `data/v3` format.
2. `src/preprocess`
   Converts raw `data/v3` batches into preprocessed `.npz` files that the dashboard can read directly.
3. `src/simulation`
   Runs virtual order simulations on raw batches and writes simulation `.npz` artifacts.
4. `gui/webUI.py`
   Starts the Panel dashboard and ties together catalog discovery, preprocessing, simulation, and interactive plots.

## Current Pipeline

```text
data/v3/*.csv
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/*-orderbook_for_plot.npz
  -> src.plotlib
  -> gui/webUI.py

data/v3/*.csv
  -> src.raw_batches
  -> src.simulation
  -> data/preprocessed/*-simulation-*.npz
  -> src.dataset_artifacts
  -> src.plotlib
  -> gui/webUI.py
```

## Project Layout

- `server/`
  - `websocket.py`: Coinbase websocket collector. Validates `sequence_num` and heartbeat continuity.
- `gui/`
  - `webUI.py`: Dashboard startup entrypoint.
  - `dashboard.py`: Main dashboard implementation, including catalog refresh, preprocessing, simulation, plot controls, and settings persistence.
  - `styles.py`: Dashboard styling and UI constants.
  - `dashboard_settings.json`: Stored simulation heatmap settings.
- `src/raw_batches/`
  - Raw CSV filename parsing, batch discovery, and loading.
- `src/preprocess/`
  - Raw batch to preprocessed `.npz` pipeline and dashboard-facing catalog helpers.
- `src/dataset_artifacts/`
  - Preprocessed and simulation artifact naming, parsing, catalog discovery, and view detection.
- `src/simulation/`
  - Virtual order simulation library, algorithm registry, parallel execution, and simulation output writing.
- `src/plotlib/`
  - Loaders, builders, and registry for orderbook, trades, and simulation heatmap plots.
- `data/`
  - `v1/`, `v2/`: Legacy formats.
  - `v3/`: Current raw CSV batch format.
  - `preprocessed/`: Base datasets and simulation artifacts.
- `docs/`
  - Module documentation, contracts, and API notes for the current architecture.
- `test/`
  - Library-level tests, refactor tests, and dashboard smoke tests.

## Installation

Create a virtual environment if you want one, then install dependencies:

```bash
pip install -r requirements.txt
```

Current dependencies in `requirements.txt`:

- `aiocsv`
- `aiofiles`
- `bokeh`
- `coinbase_advanced_py==1.8.2`
- `datashader`
- `holoviews`
- `matplotlib==3.10.8`
- `numpy`
- `pandas`
- `panel`
- `plotly`

## Running The Dashboard

Start the dashboard from the repository root:

```bash
python gui/webUI.py
```

`gui/webUI.py` currently:

- uses `data/v3` as the default raw data directory
- uses `data/preprocessed` as the default artifact directory
- starts a local Panel app with `pn.serve(..., show=True)`

## Raw Data Collection

Based on the current collector behavior, `server/websocket.py` should be run with `server/` as the working directory. It writes output files to the current working directory instead of automatically placing them under `data/`.

Important constraints:

- only one `product_id` is supported at a time
- generated filename timestamps are UTC
- the execution directory determines where `level2-*.csv` and `trade-*.csv` are written

## Data Formats

### `v1`

Legacy snapshot-only JSON. A single file can contain multiple products.

```json
{
  "PRODUCT_ID": {
    "bid": { "PRICE": "AMOUNT" },
    "offer": { "PRICE": "AMOUNT" }
  }
}
```

### `v2`

Legacy multi-product JSON event format.

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

### `v3`

The current mainline raw format is a single-product CSV batch format.

Level 2 batch files:

- `level2-PRODUCT_ID-init-yyyymmdd.hhmmss.csv`
- `level2-PRODUCT_ID-updates-yyyymmdd.hhmmss.csv`

Trade batch files:

- `trade-PRODUCT_ID-yyyymmdd.hhmmss.csv`

Columns:

- `init`

| Price | Volume | Side |
| - | - | - |

- `updates`

| Time | Price | Volume | Side |
| - | - | - | - |

- `trade`

| Time | Price | Volume | Side |
| - | - | - | - |

Notes:

- in `level2`, `Side` is `-1` for sell and `+1` for buy
- in `trade`, `Side` is currently treated by the dashboard as the taker side using `-1.0` and `1.0`
- `Time` is measured in seconds from midnight of the date encoded in the filename

## Public APIs

### `src.raw_batches`

- `discover_raw_batches(raw_dir)`
- `load_raw_batch(batch)`
- `parse_raw_filename(filename)`
- `parse_timestamp(timestamp)`
- `file_time_to_unix(file_time)`

### `src.preprocess`

- `discover_raw_batches(raw_dir, preprocessed_dir)`
- `discover_preprocessed_datasets(preprocessed_dir, ...)`
- `load_preprocessed_payload(dataset)`
- `find_simulation_files(...)`
- `has_simulation_file(...)`
- `format_time_step(...)`
- `DEFAULT_TIME_STEP`
- `PLOT_REGISTRY`
- `preprocess_batch(...)`
- `preprocess_batches(...)`

### `src.dataset_artifacts`

- `build_preprocessed_output_path(...)`
- `build_simulation_output_path(...)`
- `parse_preprocessed_filename(...)`
- `parse_simulation_filename(...)`
- `discover_preprocessed_artifacts(...)`
- `discover_simulation_artifacts(...)`
- `detect_available_views(...)`

### `src.simulation`

- `list_algorithms()`
- `load_raw_dataset(dataset)`
- `simulate_loaded_data(data, request)`
- `simulate_batch(dataset, request, output_dir)`
- `simulate_batches(datasets, request, output_dir)`
- `build_output_path(...)`

### `src.plotlib`

- `get_dataset_plot_types(dataset)`
- `get_product_plot_types(datasets)`
- `supports_plot_type(dataset, plot_type)`
- `load_plot_input(plot_type, datasets)`
- orderbook, trades, and simulation heatmap builders

## Simulation Algorithms

Currently registered algorithms:

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

Simulation outputs are currently written to:

```text
data/preprocessed/simulation-{algorithm}-{simulation_timestamp}-{seq_num}.npz
```

## Important Notes

- `server/websocket.py` currently supports only one product at a time.
- `data/preprocessed/` currently mixes two output categories:
  - `*-orderbook_for_plot.npz`
  - `*-simulation-*.npz`
- base plot availability in the dashboard is driven by the `available_views` field in the preprocessed dataset
- simulation heatmap availability is driven by whether a matching simulation artifact exists
- if you change naming rules or payload keys, update the corresponding files in `docs/` as well

## Documentation

Current module documentation lives under `docs/`:

- [docs/README.md](docs/README.md)
- [docs/raw_batches/README.md](docs/raw_batches/README.md)
- [docs/preprocess/README.md](docs/preprocess/README.md)
- [docs/dataset_artifacts/README.md](docs/dataset_artifacts/README.md)
- [docs/simulation/README.md](docs/simulation/README.md)
- [docs/plotlib/README.md](docs/plotlib/README.md)

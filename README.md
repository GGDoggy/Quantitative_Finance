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


## Simulation CLI

Run the interactive simulation helper as a repo-internal module:

```bash
python -m src.simulation
```

Legacy wrapper is still available:

```bash
python test/run_simulation.py
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

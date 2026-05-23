# Preprocess Formats and Contracts

## Raw input file contract

`src/preprocess` expects the current `v3` raw format:

### Level2 init

Filename:

- `level2-<product_id>-init-<timestamp>.csv`

Expected rows:

- `[price, volume, side]`

### Level2 updates

Filename:

- `level2-<product_id>-updates-<timestamp>.csv`

Expected rows:

- `[time_from_midnight_seconds, price, volume, side]`

### Trades

Filename:

- `trade-<product_id>-<timestamp>.csv`

Expected rows:

- `[time_from_midnight_seconds, price, volume, side]`

## Timestamp format

The package consistently uses:

- `yyyymmdd.hhmmss`

Examples:

- `20260523.000000`
- `20260523.134500`

`parse_timestamp()` converts this token into a Python `datetime`.

## Time-step token format

`format_time_step()` is used when writing filenames and labels.

Normalization rules:

- must be positive and finite
- trailing zeros are removed
- integer-valued decimals are written without `.0`

Examples:

| Input | Token |
| - | - |
| `0.01` | `0.01` |
| `1.0` | `1` |
| `0.1000` | `0.1` |

## Preprocessed orderbook filename contract

Pattern:

```text
<product_id>-<timestamp>-<time_step>-orderbook_for_plot.npz
```

Example:

```text
ETH-USD-20260523.134500-0.01-orderbook_for_plot.npz
```

This file is the core preprocess output produced by `preprocess_batch()`.

## Simulation filename contract

Supported patterns:

```text
<product_id>-<timestamp>-<time_step>-simulation-<algorithm>.npz
<product_id>-<timestamp>-<time_step>-resolved-<resolved_time>-simulation-<algorithm>.npz
```

Examples:

```text
ETH-USD-20260523.134500-0.01-simulation-event_balanced.npz
ETH-USD-20260523.134500-0.01-resolved-1-simulation-event_balanced.npz
```

Notes:

- `src/preprocess` does not generate these files.
- It only discovers and associates them with base datasets.
- Matching is tolerant to equivalent numeric tokens such as `1`, `1.0`, and normalized decimal representations.

## `.npz` payload contract

### Required orderbook keys

Any file loaded through `load_preprocessed_payload()` must contain:

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

### Optional orderbook keys

- `mid`
- `available_views`

### Trade payload keys

When the trade builder runs successfully, the merged `.npz` also contains:

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

### Runtime-added metadata

`load_preprocessed_payload()` adds these fields after reading:

- `product_id`
- `timestamp`
- `time_step`

For `PreprocessedDataset`, it also adds:

- `available_views`

## Shape contract

The validator expects:

- `price_axis.ndim == 1`
- `time_axis.ndim == 1`
- `data.ndim == 2`
- `bid.ndim == 1`
- `ask.ndim == 1`
- `bid.shape == ask.shape`
- `data.shape[0] == time_axis.shape[0]`
- `data.shape[1] == price_axis.shape[0]`

If these constraints fail, `PreprocessedDataSchemaError` is raised.

## Builder contract

Each preprocess builder in `src.plots.registry.PLOT_REGISTRY` must follow this contract:

### Input

- one `PreprocessContext`

### Output

- one `dict[str, object]` payload chunk

### Registry requirements

Each registry item declares:

- `preprocess_builder`
- `required_payload_keys`

`preprocess_batch()` only keeps a builder's output if all declared `required_payload_keys` exist in the returned chunk.

## Merge contract

All active builders write into one shared payload dict.

Allowed:

- a new key written once
- the same key written multiple times with identical value

Rejected:

- the same key written with conflicting values

Conflict handling:

- raises `PreprocessOutputConflictError`

## Discovery contract

### Raw discovery

`discover_raw_batches()` emits a `RawBatch` only when all three raw files exist for the same `(product_id, timestamp)`.

### Preprocessed discovery

`discover_preprocessed_datasets()` emits:

- one dataset for a standalone orderbook `.npz`
- one dataset per matching simulation file when simulations exist

This means one orderbook base file can expand into multiple dataset entries in the dashboard catalog.

## Extending preprocess safely

When adding a new preprocess-backed plot:

1. Add a `preprocess_builder` in `src/plots/registry.py`.
2. Return uniquely named payload keys, unless shared keys are intentionally identical.
3. Declare accurate `required_payload_keys`.
4. If the new view should be auto-detected from `.npz` content, ensure `discover_preprocessed_datasets()` can recognize it through `available_views` or `view_specs`.
5. If the plot is simulation-only, keep `preprocess_builder=None` and use simulation filename discovery instead.

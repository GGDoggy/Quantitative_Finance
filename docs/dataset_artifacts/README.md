# `src.dataset_artifacts`

`src.dataset_artifacts` owns filename rules and discovery helpers for preprocess `.npz` artifacts written into `data/preprocessed`.

## Scope

- preprocess artifact filename parsing
- `.npz` metadata validation
- available view detection for preprocess payloads

## Filename Formats

### Preprocess artifacts

```text
preprocess-{preprocess_type}-{preprocess_timestamp}.npz
```

Example:

```text
preprocess-orderbook-20260608.120000.npz
```

Old `...mmm-seq.npz` filenames are not part of the current contract and are ignored by discovery.

## Public API

- `format_time_step(...)`
- `parse_preprocessed_filename(...)`
- `build_preprocessed_output_path(...)`
- `detect_available_views(path, view_specs=None)`
- `discover_preprocessed_artifacts(preprocessed_dir, ...)`

## Main Models

### `PreprocessedArtifact`

- `product_id`
- `timestamp`
- `path`
- `available_views`
- `preprocess_type`
- `preprocess_timestamp`
- `depth`

### `DatasetLocator`

`DatasetLocator` is a lightweight reference object that can reconstruct a preprocess artifact path from stored metadata.

## Metadata Contract

Preprocess discovery requires:

- `preprocess_type`
- `preprocess_timestamp`
- `product_id`
- `timestamp`
- `file_stem`

## View Detection

`detect_available_views()` works in this order:

1. If the `.npz` file already contains `available_views`, use it directly.
2. Otherwise infer views from required payload keys.

The built-in preprocess views are:

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

For `orderbook`, key inference accepts both:

- The current snapshot contract:
  - `time_axis`, `bid_price`, `bid_size`, `ask_price`, `ask_size`, `bid`, `ask`
- The current windowed contract:
  - `time_axis__wN`, `bid_price__wN`, `bid_size__wN`, `ask_price__wN`, `ask_size__wN`, `bid__wN`, `ask__wN`
- The legacy dense-matrix contract:
  - `price_axis`, `time_axis`, `data`, `bid`, `ask`

Trade views are inferred from the unsuffixed legacy keys:

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

Current preprocess-generated trade files store `available_views` explicitly, so discovery does not need to infer trade views from windowed `trade_*__wN` keys. If a writer omits `available_views` for a windowed trade file, `detect_available_views()` will not infer `trades_scatter` or `trade_volume_timeline`.

## Discovery Ordering

`discover_preprocessed_artifacts()` returns artifacts sorted by:

1. `product_id`
2. `timestamp`
3. `preprocess_timestamp`
4. filename

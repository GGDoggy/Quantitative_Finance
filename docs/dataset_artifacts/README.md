# `src.dataset_artifacts`

`src.dataset_artifacts` owns filename rules and discovery helpers for `.npz` artifacts written into `data/preprocessed`.

## Scope

- preprocess artifact filename parsing
- analyze artifact filename parsing
- `.npz` metadata validation
- available view detection for preprocess payloads

## Filename Formats

### Preprocess artifacts

```text
preprocess-{preprocess_type}-{preprocess_timestamp}-{seq_num}.npz
```

Example:

```text
preprocess-orderbook-20260608.120000.123-0.npz
```

### Analyze artifacts

```text
analyze-{analysis_name}-{analyze_timestamp}-{seq_num}.npz
```

Example:

```text
analyze-fill_rate-20260608.120000.123-0.npz
```

## Public API

- `format_time_step(...)`
- `parse_preprocessed_filename(...)`
- `parse_analyze_filename(...)`
- `build_preprocessed_output_path(...)`
- `build_analyze_output_path(...)`
- `detect_available_views(path, view_specs=None)`
- `discover_preprocessed_artifacts(preprocessed_dir, ...)`
- `discover_analyze_artifacts(preprocessed_dir, ...)`

## Main Models

### `PreprocessedArtifact`

- `product_id`
- `timestamp`
- `path`
- `available_views`
- `preprocess_type`
- `preprocess_timestamp`
- `seq_num`
- `depth`

### `DatasetLocator`

`DatasetLocator` is a lightweight reference object that can reconstruct a preprocess artifact path from stored metadata.

### `AnalyzeArtifact`

- `product_id`
- `timestamp`
- `analysis_name`
- `path`
- `analyze_timestamp`
- `seq_num`

## View Detection

`detect_available_views()` works in this order:

1. If the `.npz` file already contains `available_views`, use it directly.
2. Otherwise infer views from required payload keys.

The built-in preprocess views are:

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

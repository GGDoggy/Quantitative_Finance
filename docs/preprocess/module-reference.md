# Preprocess Module Reference

## `service.py`

### `DEFAULT_TIME_STEP`

預設為 `0.01` 秒。

### `build_context(batch, time_step)`

載入 `RawBatch` 後建立 `PreprocessContext`。通常給直接 preprocess 用。

### `build_preprocess_context(batch, time_step, loaded_batch=None)`

如果你已經有 `LoadedRawBatch`，可以避免重複讀檔。

### `preprocess_batch(batch, output_dir, time_step=..., builder_registry=None)`

執行單一批次 preprocess，回傳 `PreprocessedDataset`。

行為要點：

- 依 registry 順序逐一呼叫 builder
- 若 builder 回傳的 payload 缺少其 `required_payload_keys`，該 view 不會列入輸出
- 多個 builder 若對同一 key 產出不同內容，會丟 `PreprocessOutputConflictError`
- 最後以暫存檔寫入 `.npz`，再 replace 成正式輸出

### `preprocess_batches(...)`

逐批次 preprocess，支援 `progress_callback(message)`。

## `registry.py`

### `PreprocessBuilderSpec`

欄位：

- `preprocess_builder`
- `required_payload_keys`

### `PLOT_REGISTRY`

目前固定註冊：

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

## `datasets.py`

### `discover_preprocessed_datasets(preprocessed_dir, ...)`

實際轉呼叫 `src.dataset_artifacts.discover_preprocessed_artifacts(...)`。

### `discover_raw_batches(raw_dir, preprocessed_dir)`

先掃 raw batches，再對照 preprocessed catalog，把 `RawBatch.is_preprocessed` 標出來。

### `find_simulation_files(...)`

用 artifact metadata 條件過濾 simulation `.npz`。

### `has_simulation_file(...)`

布林版的 `find_simulation_files(...)`。

### `load_preprocessed_payload(dataset)`

讀取 `.npz`、驗證 schema、把 `product_id` / `timestamp` / `time_step` 注入 payload。

如果傳入的是 `DatasetLocator`，可使用其 `payload_cache` 避免重複載入。

## `models.py`

### `PreprocessContext`

builder 的標準輸入物件，包含：

- `batch`
- `time_step`
- `init_rows`
- `updates_rows`
- `trade_rows`

## `exceptions.py`

- `PreprocessError`
- `PreprocessValidationError`
- `PreprocessOutputConflictError`
- `PreprocessedDataError`
- `PreprocessedDataFileError`
- `PreprocessedDataSchemaError`

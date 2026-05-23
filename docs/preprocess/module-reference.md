# Preprocess Module Reference

## `src/preprocess/catalog.py`

這個模組提供 dashboard 偏向的 catalog 與 payload helper。

### 主要函式

- `format_time_step(...)`
  - 包裝 `src.dataset_artifacts.format_time_step()`，改丟 `PreprocessValidationError`
- `detect_available_views(path, view_specs=None)`
  - 重新推斷 `.npz` 可支援的 views
- `find_simulation_files(...)`
  - 依 product / timestamp / time_step / algorithm 等條件找 simulation `.npz`
- `has_simulation_file(...)`
  - 判斷某 base dataset 是否已有 simulation artifact
- `discover_preprocessed_datasets(preprocessed_dir, ...)`
  - 直接代理到 `discover_preprocessed_artifacts()`
- `discover_raw_batches(raw_dir, preprocessed_dir)`
  - 在 raw discovery 上補 `is_preprocessed`
- `load_preprocessed_payload(dataset)`
  - 讀 `.npz` 成 `dict[str, object]`，並做 schema validation

## `src/preprocess/pipeline.py`

這個模組是實際的 preprocess pipeline。

### 主要資料結構

- `PreprocessContext`
  - `batch`
  - `time_step`
  - `init_rows`
  - `updates_rows`
  - `trade_rows`
- `PreprocessBuilderSpec`
  - `preprocess_builder`
  - `required_payload_keys`

### 主要函式

- `build_trade_arrays(trade_rows, timestamp)`
  - 將 raw trades 轉成 numpy arrays
- `build_trade_payload(context)`
  - 產生 trades 視圖共用 payload
- `build_context(batch, time_step)`
  - 載入 raw batch 並建立 `PreprocessContext`
- `build_preprocess_context(batch, time_step, loaded_batch=None)`
  - 允許重用已載入資料
- `preprocess_batch(batch, output_dir, time_step=DEFAULT_TIME_STEP, builder_registry=None)`
  - 將單一 batch 寫成 `.npz`
- `preprocess_batches(batches, output_dir, ...)`
  - 逐批處理並支援 progress callback

### `PLOT_REGISTRY`

目前 registry 如下：

```python
{
    "orderbook": ...,
    "trades_scatter": ...,
    "trade_volume_timeline": ...,
}
```

這裡決定兩件事：

- preprocess 會產生哪些 payload
- dashboard 對 base dataset 可提供哪些 plot 類型

## `src/preprocess/orderbook.py`

這個模組負責 orderbook payload 的核心建構邏輯。`pipeline.py` 並不實作 orderbook 細節，而是透過：

```python
PreprocessBuilderSpec(
    preprocess_builder=build_orderbook_payload,
    required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
)
```

把它接進 registry。

## 例子

```python
from pathlib import Path

from src.preprocess import discover_raw_batches, preprocess_batch

raw_dir = Path("data/v3")
preprocessed_dir = Path("data/preprocessed")
batches = discover_raw_batches(raw_dir, preprocessed_dir)

dataset = preprocess_batch(batches[0], preprocessed_dir)
print(dataset.path)
print(dataset.available_views)
```

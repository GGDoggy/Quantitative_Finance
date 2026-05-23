# `src.preprocess`

`src.preprocess` 只負責把一個 `RawBatch` 轉成 dashboard 可讀取的 preprocessed `.npz`。

它不再負責：

- 原始 CSV 批次 discovery
- simulation artifact discovery
- `.npz` 命名規則定義

這些職責已移到：

- `src.raw_batches`
- `src.dataset_artifacts`

## Current responsibilities

- 建立 `PreprocessContext`
- 執行 preprocess builders
- 合併 payload chunk
- 寫出 preprocessed artifact
- 驗證並載入 preprocessed payload

## Main APIs

- `preprocess_batch(batch, output_dir, time_step=...)`
- `preprocess_batches(batches, output_dir, time_step=...)`
- `load_preprocessed_payload(dataset)`

## Internal structure

- `service.py`
  - preprocess orchestration
- `builders/`
  - orderbook 與 trades payload builders
- `registry.py`
  - preprocess builder registry
- `datasets.py`
  - artifact discovery compatibility wrapper + payload loading
- `models.py`
  - `PreprocessContext`

## Upstream / downstream

Flow:

1. `src.raw_batches.discover_raw_batches()` 找到完整 raw batch
2. `src.preprocess.preprocess_batch()` 產生 preprocessed `.npz`
3. `src.dataset_artifacts.discover_preprocessed_artifacts()` 建立 artifact catalog
4. `src.plotlib.loaders.*` 讀取 artifact 並 render

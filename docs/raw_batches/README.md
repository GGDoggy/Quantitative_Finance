# `src.raw_batches`

`src.raw_batches` 封裝 `data/v3` 原始 CSV 批次的檔名規則、批次探索與載入。它是 preprocess 和 simulation 的共同上游。

## 責任範圍

- 解析 raw CSV 檔名
- 將三個 CSV 檔案配對成一個 `RawBatch`
- 將 `RawBatch` 載入成記憶體中的 rows
- 提供 timestamp parsing 與 unix time 轉換

## 原始批次組成

一個完整批次必須同時包含三個檔案：

- `level2-{product_id}-init-{timestamp}.csv`
- `level2-{product_id}-updates-{timestamp}.csv`
- `trade-{product_id}-{timestamp}.csv`

`discover_raw_batches(...)` 只會回傳三者都齊全的批次。

## 主要 API

- `parse_raw_filename(filename)`
  - 回傳 `RawFilenameMetadata(product_id, timestamp, kind)`，`kind` 為 `init`、`updates`、`trade`
- `discover_raw_batches(raw_dir)`
  - 掃描目錄並回傳 `list[RawBatch]`
- `load_raw_batch(batch)`
  - 讀取三個 CSV，回傳 `LoadedRawBatch`
- `parse_timestamp(timestamp)`
  - 解析 `YYYYMMDD.HHMMSS`
- `file_time_to_unix(timestamp)`
  - 轉成 UTC unix seconds

## `RawBatch`

`RawBatch` 是整個 repo 用來識別單一原始批次的核心物件，欄位包含：

- `product_id`
- `timestamp`
- `init_path`
- `updates_path`
- `trade_path`
- `is_preprocessed`

其中 `is_preprocessed` 不是 discovery 的原生資訊；它通常由 `src.preprocess.datasets.discover_raw_batches(...)` 根據 preprocessed catalog 補上。

## `LoadedRawBatch`

`load_raw_batch(...)` 回傳：

- `init`
- `updates`
- `trades`
- `start_time`

CSV 內容使用 `csv.QUOTE_NONNUMERIC` 讀入，因此每一列會被轉為 `list[float]`。

## 與其他模組的關係

- `src.preprocess.service` 先用它把 `RawBatch` 載入，再建立 `PreprocessContext`
- `src.simulation.io` 先用它把 `RawBatch` 轉成 `LoadedMarketData`
- `src.dataset_artifacts` 不依賴它的 CSV 內容，但會重用其 timestamp parsing

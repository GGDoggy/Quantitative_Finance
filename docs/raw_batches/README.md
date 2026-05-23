# `src.raw_batches`

`src.raw_batches` 是 `data/v3` 原始 CSV 批次的最底層入口，負責三件事：

- 依檔名把同一個時間戳的 `init` / `updates` / `trade` 三個 CSV 組成 `RawBatch`
- 將檔名中的 `YYYYMMDD.HHMMSS` 轉成 `datetime` 或 unix seconds
- 讀取 CSV，輸出 `LoadedRawBatch`

這個模組不關心 preprocess、simulation 或 dashboard，只處理原始資料批次本身。

## 檔名規則

目前支援的 raw CSV 檔名如下：

```text
level2-{product_id}-init-{timestamp}.csv
level2-{product_id}-updates-{timestamp}.csv
trade-{product_id}-{timestamp}.csv
```

其中：

- `product_id` 例如 `ETH-USD`
- `timestamp` 格式固定為 `YYYYMMDD.HHMMSS`

只有當同一組 `(product_id, timestamp)` 同時存在 `init`、`updates`、`trade` 三個檔案時，`discover_raw_batches()` 才會回傳對應的 `RawBatch`。

## Public API

- `parse_timestamp(timestamp: str) -> datetime`
- `file_time_to_unix(file_time: str) -> int`
- `parse_raw_filename(filename: str) -> RawFilenameMetadata | None`
- `discover_raw_batches(raw_dir: Path | str) -> list[RawBatch]`
- `load_raw_batch(batch: RawBatch) -> LoadedRawBatch`

## 主要資料模型

### `RawBatch`

`RawBatch` 代表一組完整原始批次，欄位包括：

- `product_id`
- `timestamp`
- `init_path`
- `updates_path`
- `trade_path`
- `is_preprocessed`

便利屬性：

- `batch_id`
  - 例如 `ETH-USD|20240501.120000`
- `file_stem`
  - 例如 `ETH-USD-20240501.120000`
- `display_name`
  - 給 dashboard 顯示的人類可讀字串

### `LoadedRawBatch`

`load_raw_batch()` 會把三個 CSV 讀進記憶體，回傳：

- `init: list[list[float]]`
- `updates: list[list[float]]`
- `trades: list[list[float]]`
- `start_time: float`

目前 CSV reader 使用 `csv.QUOTE_NONNUMERIC`，因此數值欄位會直接轉為 `float`。

## 跟其他模組的關係

- `src.preprocess.pipeline.build_context()` 會先呼叫 `load_raw_batch()`
- `src.simulation.service.load_raw_dataset()` 也會透過 `load_raw_batch()` 讀原始資料
- `src.preprocess.catalog.discover_raw_batches()` 在這層 discovery 之上，再補上 `is_preprocessed` 標記

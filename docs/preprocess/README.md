# `src.preprocess`

`src.preprocess` 把 `RawBatch` 轉成 dashboard 可直接使用的 preprocessed `.npz`。目前主實作集中在：

- [formats-and-contracts.md](formats-and-contracts.md)
- [module-reference.md](module-reference.md)

## 目前入口

- catalog 與 payload helpers 在 `src/preprocess/catalog.py`
- preprocess pipeline 在 `src/preprocess/pipeline.py`
- orderbook payload builder 在 `src/preprocess/orderbook.py`

## 主流程

```text
RawBatch
  -> build_context()
  -> PreprocessContext
  -> PLOT_REGISTRY 逐項執行 preprocess_builder
  -> merge payload chunks
  -> write *.npz
  -> discover_preprocessed_artifacts() 回傳 PreprocessedArtifact
```

## Public API

從 `src.preprocess` 匯出的主要項目：

- catalog
  - `discover_raw_batches(raw_dir, preprocessed_dir)`
  - `discover_preprocessed_datasets(preprocessed_dir, ...)`
  - `load_preprocessed_payload(dataset)`
  - `find_simulation_files(...)`
  - `has_simulation_file(...)`
  - `detect_available_views(...)`
  - `format_time_step(...)`
  - `parse_timestamp(...)`
- pipeline
  - `DEFAULT_TIME_STEP`
  - `PLOT_REGISTRY`
  - `PreprocessContext`
  - `PreprocessBuilderSpec`
  - `preprocess_batch(...)`
  - `preprocess_batches(...)`

## 目前支援的 preprocess views

`PLOT_REGISTRY` 目前有三種 base view：

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

其中：

- `trades_scatter` 與 `trade_volume_timeline` 共用同一組 trades payload builder
- simulation heatmaps 不在 preprocess 階段產生，它們依賴另外寫出的 simulation `.npz`

## 重要設計點

- `discover_raw_batches(raw_dir, preprocessed_dir)` 會把 raw discovery 和 preprocessed catalog 串起來，補出 `is_preprocessed`
- `preprocess_batch()` 在寫檔前會 merge 各 builder 輸出的 payload，如果同 key 值衝突，會拋出 `PreprocessOutputConflictError`
- output path 不在 preprocess 模組硬編碼，而是交由 `src.dataset_artifacts.build_preprocessed_output_path()` 處理

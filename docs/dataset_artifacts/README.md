# `src.dataset_artifacts`

`src.dataset_artifacts` 負責管理 `data/preprocessed` 內各種 `.npz` artifact 的命名、解析、探索與定位。它不處理資料內容本身，而是提供上層模組一套穩定的檔名 contract 與 metadata model。

## 責任範圍

- 定義 preprocessed orderbook artifact 檔名格式
- 定義 simulation artifact 檔名格式
- 解析檔名回 `product_id`、`timestamp`、`time_step`、`resolved_time`、`algorithm_name`
- 掃描目錄並整理成 `PreprocessedArtifact` / `SimulationArtifact`
- 為 GUI 或 loader 提供可延遲解析的 `DatasetLocator`
- 根據 `.npz` 內容推斷 `available_views`

## 主要檔案

- `naming.py`
  - `format_time_step(...)`
  - `format_resolved_time(...)`
  - `parse_preprocessed_filename(...)`
  - `parse_simulation_filename(...)`
  - `build_preprocessed_output_path(...)`
  - `build_simulation_output_path(...)`
- `models.py`
  - `SimulationArtifact`
  - `PreprocessedArtifact`
  - `DatasetLocator`
- `discovery.py`
  - `discover_preprocessed_artifacts(...)`
  - `discover_simulation_artifacts(...)`
  - `detect_available_views(...)`

## 檔名規則

Preprocessed orderbook dataset:

```text
{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz
```

Simulation dataset:

```text
{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}-simulation-{algorithm_name}.npz
```

其中 `timestamp` 格式固定為 `YYYYMMDD.HHMMSS`。

## `PreprocessedArtifact`

`PreprocessedArtifact` 是 GUI / catalog 層最常使用的 model，包含：

- `product_id`
- `timestamp`
- `time_step`
- `path`
- `available_views`
- `simulation_artifact`

當 `simulation_artifact is None` 時，代表它只對應 preprocessed orderbook/trades payload。

當 `simulation_artifact` 有值時，代表它是「同一組 base dataset + 一個 simulation artifact」的組合視圖，`available_views` 會把 orderbook/trades view 和 simulation heatmap view 合併起來。

## `available_views` 判斷方式

`detect_available_views(...)` 會優先讀 `.npz` 裡的 `available_views` 欄位；如果缺少這個欄位，會退回用 key set 推斷：

- `orderbook`: 需要 `price_axis`, `time_axis`, `data`, `bid`, `ask`
- `trades_scatter`: 需要 `trade_time`, `trade_price`, `trade_volume`, `trade_side`
- `trade_volume_timeline`: 需要 `trade_time`, `trade_price`, `trade_volume`, `trade_side`

Simulation 類 view 不由 payload key 自動判定，而是在 `discover_preprocessed_artifacts(...)` 裡透過是否發現 simulation artifact 來補入：

- `fill_probability`
- `mid_profit`
- `micro_profit`
- `mid_fill_probability_cost`
- `micro_fill_probability_cost`

## 與其他模組的關係

- `src.preprocess` 用它產生 preprocessed 輸出檔名，並重新掃描剛寫出的 artifact
- `src.simulation` 用它產生 simulation 輸出檔名
- `src.preprocess.datasets` 和 GUI 層用它做 catalog discovery
- `src.plotlib` 不直接依賴它的 discovery，但會消費它指向的 `.npz` 檔案

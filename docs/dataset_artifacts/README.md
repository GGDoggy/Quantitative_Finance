# `src.dataset_artifacts`

`src.dataset_artifacts` 專門處理 `data/preprocessed` 內各種 `.npz` artifact 的命名、解析與 catalog。它是 preprocess、simulation、dashboard 之間的共享契約層。

## 負責範圍

- preprocessed dataset 檔名的建構與解析
- simulation artifact 檔名的建構與解析
- 掃描 `data/preprocessed` 並建立 artifact 清單
- 從 `.npz` keys 推斷 `available_views`
- 把 base dataset 與對應 simulation artifact 關聯起來

## 檔名規則

### Preprocessed dataset

```text
{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz
```

例子：

```text
ETH-USD-20240501.120000-0.01-orderbook_for_plot.npz
```

### Simulation dataset

```text
{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}-depth-{order_depth}-simulation-{algorithm_name}.npz
```

例子：

```text
ETH-USD-20240501.120000-0.01-resolved-1-depth-3-simulation-event_balanced.npz
```

## Public API

- `format_time_step(...)`
- `format_resolved_time(...)`
- `parse_preprocessed_filename(...)`
- `parse_simulation_filename(...)`
- `build_preprocessed_output_path(...)`
- `build_simulation_output_path(...)`
- `detect_available_views(path, view_specs=None)`
- `discover_preprocessed_artifacts(preprocessed_dir, ...)`
- `discover_simulation_artifacts(preprocessed_dir, ...)`

## 主要資料模型

### `SimulationArtifact`

- `product_id`
- `timestamp`
- `time_step`
- `algorithm_name`
- `path`
- `time_step_token`
- `resolved_time`
- `resolved_time_token`
- `order_depth`

### `PreprocessedArtifact`

- `product_id`
- `timestamp`
- `time_step`
- `path`
- `available_views`
- `time_step_token`
- `simulation_artifact`

重點：

- `simulation_artifact is None`
  - 代表單純的 preprocessed dataset
- `simulation_artifact is not None`
  - 代表同一個 base dataset 搭配一個 simulation artifact 的組合視圖

便利屬性：

- `resolved_time`
- `algorithm_name`
- `simulation_path`
- `dataset_id`
- `display_name`

### `DatasetLocator`

`DatasetLocator` 主要給 dashboard / payload cache 使用，用來延遲解析 base dataset 路徑與 simulation 關聯。

## `available_views`

`detect_available_views()` 的判斷方式如下：

- 若 `.npz` 內已有 `available_views` key，直接採用
- 否則依 `view_specs` 或預設 key 組合推斷

預設可偵測的 base views：

- `orderbook`
  - 需要 `price_axis`, `time_axis`, `data`, `bid`, `ask`
- `trades_scatter`
  - 需要 `trade_time`, `trade_price`, `trade_volume`, `trade_side`
- `trade_volume_timeline`
  - 需要 `trade_time`, `trade_price`, `trade_volume`, `trade_side`

simulation 相關 view key 目前固定補入：

- `fill_probability`
- `mid_profit`
- `micro_profit`
- `mid_fill_probability_cost`
- `micro_fill_probability_cost`

## 跟其他模組的關係

- `src.preprocess.pipeline` 透過 `build_preprocessed_output_path()` 寫出 base dataset
- `src.simulation.service` 透過 `build_simulation_output_path()` 寫出 simulation artifact
- `src.preprocess.catalog` 用 `discover_preprocessed_artifacts()` 建立 dashboard catalog
- `src.plotlib.registry` 依 `available_views` 和 `simulation_artifact` 決定圖表可用性

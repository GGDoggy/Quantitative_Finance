# Plotlib Architecture

## 高層流程

```text
PreprocessedArtifact
  -> src.plotlib.registry.load_plot_input()
  -> loader
  -> normalized payload / simulation arrays
  -> builder
  -> HoloViews object or Plotly Figure
  -> gui.dashboard render
```

## `registry.py`

`APP_PLOT_REGISTRY` 中每一項 `DashboardPlotSpec` 都定義：

- `plot_type`
- `label`
- `loader`
- `builder`
- `required_payload_keys`
- `requires_simulation`

這讓 dashboard 不需要知道各 plot 的實作細節，只需要：

1. 依 dataset 找出可支援的 plot types
2. 依 plot type 載入對應輸入
3. 呼叫 builder 產生圖

## Base dataset 路徑

### Orderbook

- loader: `load_orderbook_payloads(...)`
- builder: `build_orderbook_view(...)`
- 資料來源: preprocessed `.npz`

### Trades

- loader: `load_trades_payloads(...)`
- builder: `build_trades_scatter_view(...)` 或 `build_trade_volume_timeline_view(...)`
- 資料來源: 同一份 preprocessed `.npz`

## Simulation heatmap 路徑

### Fill / profit / cost-filtered plots

- loader: `load_simulation_arrays_from_metadata(...)`
- builder:
  - `build_fill_probability_view(...)`
  - `build_mid_profit_view(...)`
  - `build_micro_profit_view(...)`
  - `build_mid_cost_fill_probability_view(...)`
  - `build_micro_cost_fill_probability_view(...)`
- 資料來源: simulation `.npz`

## Payload normalization

`types.py` 內的 normalization helper 會把 loader 輸出的資料正規化成 schema version `1`。builder 在接收 payload 前，預期資料已經是 version `1`。

這樣的好處是：

- loader 負責處理舊資料或格式差異
- builder 只專注於視覺化
- schema 升級時有單一轉換入口

## Dashboard 端的使用方式

`gui/dashboard.py` 主要使用這幾個函式：

- `get_dataset_plot_types(dataset)`
- `get_product_plot_types(datasets)`
- `supports_plot_type(dataset, plot_type)`
- `load_plot_input(plot_type, datasets)`

這代表 dashboard 與 plot 實作是鬆耦合的；新增圖表通常只要補：

- `src/plotlib/registry.py`
- 對應 loader / builder
- 必要時補 `src/preprocess/pipeline.py` 或 simulation 輸出支援

# `src.plotlib`

`src.plotlib` 是 dashboard 的繪圖層。它不負責 raw discovery 或 preprocess，而是把既有 `.npz` 轉成可渲染的 HoloViews 或 Plotly 物件。

細節請看：

- [architecture.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/architecture.md)
- [api.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/api.md)

## 模組分工

- `orderbook.py`
  - 讀取 orderbook payload，建構 HoloViews orderbook view
- `trades.py`
  - 讀取 trades payload，建構 Plotly trades views
- `simulation_heatmaps.py`
  - 讀取 simulation arrays，建構 fill probability / profit / cost-filtered heatmaps
- `registry.py`
  - 定義 dashboard 可見 plot types、label、loader、builder 與是否需要 simulation
- `types.py`
  - 正規化 payload 到 schema version `1`
- `options.py`
  - heatmap 設定與 render options

## 目前支援的圖

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`
- `fill_probability`
- `mid_profit`
- `micro_profit`
- `mid_fill_probability_cost`
- `micro_fill_probability_cost`

## 重要設計點

- `src.plotlib.registry.APP_PLOT_REGISTRY` 是 dashboard plot 選單的單一來源
- base dataset 的可畫圖能力由 `dataset.available_views` 決定
- simulation heatmap 是否可用由 `dataset.simulation_artifact is not None` 決定

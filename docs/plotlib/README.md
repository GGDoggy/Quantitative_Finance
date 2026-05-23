# `src.plotlib`

`src.plotlib` 是目前 repo 的繪圖核心。它把 preprocessed / simulation `.npz` 轉成型別化 payload，並提供對外穩定的 view-building API。

和舊版 `src.plots` 相比，現在的設計更明確分成三層：

1. `loaders/`
   - 從檔案讀出 payload 或 simulation arrays
2. `types.py`
   - 正規化成 `V1` payload schema
3. `views.py` / `renderers/`
   - 建立實際圖表物件

## 提供的 view

- `build_orderbook_view(...)`
- `build_trades_scatter_view(...)`
- `build_trade_volume_timeline_view(...)`
- `build_fill_probability_view(...)`
- `build_mid_profit_view(...)`
- `build_micro_profit_view(...)`
- `build_mid_cost_fill_probability_view(...)`
- `build_micro_cost_fill_probability_view(...)`

## 輸入資料來源

- orderbook / trades 視圖：
  - 使用 preprocess 產出的 `.npz`
- simulation heatmap 視圖：
  - 使用 simulation 產出的 `.npz`

## 主要模組

- `views.py`
  - 對外公開的薄 wrapper
- `types.py`
  - `OrderbookPayloadV1`
  - `TradesPayloadV1`
  - `SimulationArraysV1`
- `options.py`
  - heatmap 軸與顏色範圍設定
- `loaders/`
  - orderbook / trades / simulation 載入器
- `renderers/`
  - 實際圖表建立邏輯

## schema version

`src.plotlib` 目前把所有輸入正規化到 `schema_version == "1"`。

renderers 會依賴這個欄位；若 schema 不符，會丟 `PayloadSchemaVersionError`。

## 相關文件

- [api.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/api.md)
- [architecture.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/architecture.md)

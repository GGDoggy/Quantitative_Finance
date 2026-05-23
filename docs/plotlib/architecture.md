# Plotlib Architecture

## 分層

### 1. Loader layer

負責把 `.npz` 讀成乾淨的 Python / NumPy payload：

- `loaders/orderbook.py`
- `loaders/trades.py`
- `loaders/simulation.py`

這一層負責：

- 檢查必要 keys 是否存在
- 必要時做 dtype / datetime 轉換
- 呼叫 `normalize_*_to_v1(...)`

### 2. Type normalization layer

`types.py` 把不同來源的 dict 正規化成明確的 `V1` schema，並補齊必要欄位，例如：

- 補 `schema_version = "1"`
- orderbook 若沒有 `mid`，自動用 `0.5 * (bid + ask)` 補上

### 3. View API layer

`views.py` 提供穩定入口，避免呼叫端直接依賴 renderer 細節。

### 4. Renderer layer

`renderers/` 內放實際繪圖邏輯：

- `orderbook.py`
- `trades_scatter.py`
- `trade_volume_timeline.py`
- `fill_probability.py`
- `profit_heatmap.py`
- `cost_fill_probability.py`
- `simulation_common.py`
- `trades_common.py`

## 交易視圖限制

`renderers/trades_common.py` 會把多個 trade payload 合併成單一 DataFrame，但要求：

- 每筆資料都帶有 `product_id`
- 所有 payload 必須來自同一個 `product_id`
- 資料不能是空的

這代表目前 trade 類 view 不支援跨商品聚合。

## Simulation heatmap 共用邏輯

`renderers/simulation_common.py` 提供：

- bin edge / center 計算
- heatmap trace 建立
- sample count 共用 color 上限
- 正方形 heatmap 軸設定

目前預設 `RESOLVED_ONLY = True`，顯示邏輯以 resolved outcome 為主。

## 與上游 / 下游的關係

上游：

- `src.preprocess` 提供 orderbook/trade `.npz`
- `src.simulation` 提供 simulation `.npz`

下游：

- GUI dashboard 或其他應用層負責選 dataset、呼叫 loader / view builder、把結果放到 Panel 或 Plotly 容器內

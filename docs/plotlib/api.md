# Plotlib API

## Public imports

`src.plotlib.__init__` 目前對外暴露三類 API：

- view builders
- payload / options 型別
- error types

## View builders

### `build_orderbook_view(payloads, render_options=None)`

輸入 `list[OrderbookPayloadV1]`，建立 orderbook 視圖。

### `build_trades_scatter_view(trade_frames_or_payloads, render_options=None)`

輸入可為：

- `Sequence[TradesPayloadV1]`
- 含 `Time`, `Price`, `Volume`, `Side` 欄位的 `pandas.DataFrame`

### `build_trade_volume_timeline_view(trade_frames_or_payloads, render_options=None)`

輸入型別與 `build_trades_scatter_view(...)` 相同。

### `build_fill_probability_view(simulation_arrays, render_options=None)`

輸入 `SimulationArraysV1`。

### `build_mid_profit_view(simulation_arrays, render_options=None)`

輸入 `SimulationArraysV1`。

### `build_micro_profit_view(simulation_arrays, render_options=None)`

輸入 `SimulationArraysV1`。

### `build_mid_cost_fill_probability_view(simulation_arrays, render_options=None)`

輸入 `SimulationArraysV1`，並使用 `render_options.cost`。

### `build_micro_cost_fill_probability_view(simulation_arrays, render_options=None)`

輸入 `SimulationArraysV1`，並使用 `render_options.cost`。

## Loaders

### `load_orderbook_payload(path, product_id, timestamp, time_step)`

要求 `.npz` 至少包含：

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

可選：

- `mid`

### `load_trades_payload(path, product_id, timestamp, time_step)`

要求 `.npz` 包含：

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

### `load_simulation_arrays(paths)`

可一次讀多個 simulation artifact，再串接成單一 `SimulationArraysV1`。

要求每個 `.npz` 都包含：

- `bid_near_size`
- `bid_opp_size`
- `bid_mid_profit`
- `bid_micro_profit`
- `bid_result`
- `ask_near_size`
- `ask_opp_size`
- `ask_mid_profit`
- `ask_micro_profit`
- `ask_result`

## 型別

### `OrderbookPayloadV1`

至少包含：

- `schema_version`
- `product_id`
- `timestamp`
- `time_step`
- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`
- `mid`

### `TradesPayloadV1`

- `schema_version`
- `product_id`
- `timestamp`
- `time_step`
- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

### `SimulationArraysV1`

- `schema_version`
- `bid_near_size`
- `bid_opp_size`
- `bid_result`
- `ask_near_size`
- `ask_opp_size`
- `ask_result`
- `bid_mid_profit`
- `ask_mid_profit`
- `bid_micro_profit`
- `ask_micro_profit`

## Render options

### `PlotRenderOptions`

欄位：

- `cost`
- `simulation_heatmap_settings`

### `DashboardSimulationHeatmapSettings`

分成三組設定：

- `fill_probability`
- `profit`
- `conditional_fill_probability`

它支援 `to_dict()` / `from_dict(...)`，供 GUI 設定檔序列化使用。

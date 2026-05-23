# Plotlib API

## Public exports

`src.plotlib.__init__` 目前對外提供四類能力：

### 1. Plot registry

- `APP_PLOT_LABELS`
- `APP_PLOT_REGISTRY`
- `DashboardPlotSpec`
- `get_dataset_plot_types(dataset)`
- `get_product_plot_types(datasets)`
- `supports_plot_type(dataset, plot_type)`
- `load_plot_input(plot_type, datasets)`

### 2. Orderbook plots

- `load_orderbook_payload(path, *, product_id, timestamp, time_step)`
- `load_orderbook_payloads(datasets)`
- `build_orderbook_view(payloads, render_options=None)`

### 3. Trades plots

- `load_trades_payload(path, *, product_id, timestamp, time_step)`
- `load_trades_payloads(datasets)`
- `build_trades_scatter_view(payloads_or_frames, render_options=None)`
- `build_trade_volume_timeline_view(payloads_or_frames, render_options=None)`

### 4. Simulation heatmaps

- `load_simulation_arrays(paths)`
- `load_simulation_arrays_from_metadata(simulation_paths)`
- `build_fill_probability_view(simulation_arrays, render_options=None)`
- `build_mid_profit_view(simulation_arrays, render_options=None)`
- `build_micro_profit_view(simulation_arrays, render_options=None)`
- `build_mid_cost_fill_probability_view(simulation_arrays, render_options=None)`
- `build_micro_cost_fill_probability_view(simulation_arrays, render_options=None)`

## Plot type 與資料需求

| Plot type | Base data | Simulation data |
| --- | --- | --- |
| `orderbook` | 需要 | 不需要 |
| `trades_scatter` | 需要 | 不需要 |
| `trade_volume_timeline` | 需要 | 不需要 |
| `fill_probability` | 不需要 | 需要 |
| `mid_profit` | 不需要 | 需要 |
| `micro_profit` | 不需要 | 需要 |
| `mid_fill_probability_cost` | 不需要 | 需要 |
| `micro_fill_probability_cost` | 不需要 | 需要 |

## 主要錯誤類型

- `PayloadSchemaVersionError`
  - payload schema version 不是 builder 預期值
- `PreprocessedDataError`
  - 載入 `.npz` 失敗或缺必要欄位
- `FileNotFoundError`
  - 指定 dataset 路徑不存在

## 例子

```python
from src.plotlib import build_trades_scatter_view, load_trades_payload

payload = load_trades_payload(
    "data/preprocessed/ETH-USD-20240501.120000-0.01-orderbook_for_plot.npz",
    product_id="ETH-USD",
    timestamp="20240501.120000",
    time_step=0.01,
)
figure = build_trades_scatter_view([payload])
```

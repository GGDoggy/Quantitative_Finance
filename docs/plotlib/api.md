# `src.plotlib` API

## Public builders

- `build_orderbook_view(payloads, render_options=None)`
- `build_trades_scatter_view(payloads, render_options=None)`
- `build_trade_volume_timeline_view(payloads, render_options=None)`
- `build_fill_probability_view(arrays, render_options=None)`
- `build_mid_profit_view(arrays, render_options=None)`
- `build_micro_profit_view(arrays, render_options=None)`
- `build_mid_cost_fill_probability_view(arrays, render_options=None)`
- `build_micro_cost_fill_probability_view(arrays, render_options=None)`

## Loaders

- `load_orderbook_payload(...)`
- `load_orderbook_payloads(...)`
- `load_trades_payload(...)`
- `load_trades_payloads(...)`
- `load_simulation_arrays(...)`

artifact discovery API 已移出 `src.plotlib`，改由 `src.dataset_artifacts` 提供。

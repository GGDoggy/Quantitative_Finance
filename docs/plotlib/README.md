# `src.plotlib`

`src.plotlib` 是目前唯一的 plotting library entrypoint。

它只負責：

- 讀取已存在的 preprocessed / simulation artifact
- 正規化 payload
- 建立 plotting view

它不再負責：

- raw batch discovery
- artifact naming / discovery
- simulation filename parsing

這些職責已移到：

- `src.raw_batches`
- `src.dataset_artifacts`

## Public builders

- `build_orderbook_view`
- `build_trades_scatter_view`
- `build_trade_volume_timeline_view`
- `build_fill_probability_view`
- `build_mid_profit_view`
- `build_micro_profit_view`
- `build_mid_cost_fill_probability_view`
- `build_micro_cost_fill_probability_view`

# Simulation Data Format

本文件描述 `src.simulation` 寫出的 `.npz` 檔案格式，以及 `src.plotlib.loaders.simulation` 對其最低要求。

## 檔名格式

```text
{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}-simulation-{algorithm_name}.npz
```

範例：

```text
ETH-USD-20240501.120000-0.01-resolved-1-simulation-event_balanced.npz
```

## Metadata keys

`save_result_file(...)` 目前會寫入：

- `algorithm`
- `product_id`
- `file_stem`
- `time_step`
- `base_tick`
- `resolved_time`

這些 key 定義在 `SIMULATION_METADATA_KEYS`。

## Result keys

`SimulationResult` 會序列化成以下欄位，順序由 `SIMULATION_RESULT_KEYS` 定義：

- `bid_prices`
- `bid_near_size`
- `bid_opp_size`
- `bid_survival_time`
- `bid_ahead`
- `bid_behind`
- `bid_vorder_ratio`
- `bid_result`
- `bid_spread`
- `ask_prices`
- `ask_near_size`
- `ask_opp_size`
- `ask_survival_time`
- `ask_ahead`
- `ask_behind`
- `ask_vorder_ratio`
- `ask_result`
- `ask_spread`
- `bid_mid_price`
- `bid_micro_price`
- `bid_mid_profit`
- `bid_micro_profit`
- `ask_mid_price`
- `ask_micro_price`
- `ask_mid_profit`
- `ask_micro_profit`

## Plotlib 最低需求

`src.plotlib.loaders.simulation.load_simulation_arrays(...)` 並不要求讀取全部 simulation result keys，它目前只依賴：

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

換句話說：

- `.npz` 可以包含更多 simulation 結果欄位
- 但如果缺少上面十個 key，heatmap loader 會失敗

## 多檔合併

`load_simulation_arrays(paths)` 支援一次讀多個 simulation 檔，並對每個 required key 做 `np.concatenate(...)`。這讓 GUI 可以把同一組條件下的多個 artifact 合併成一份 heatmap 輸入。

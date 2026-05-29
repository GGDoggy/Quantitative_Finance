# Simulation Data Format

這份文件描述 simulation `.npz` 的輸出格式，也就是：

```text
simulation-{algorithm_name}-{simulation_timestamp}.npz
```

## Metadata keys

每個 simulation `.npz` 目前至少包含：

- `algorithm`
- `simulation_timestamp`
- `product_id`
- `timestamp`
- `file_stem`
- `time_step`
- `base_tick`
- `resolved_time`
- `depth`

## Array keys

目前 `save_result_file()` 會依 `SIMULATION_RESULT_KEYS` 寫出以下欄位：

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

## 給 `src.plotlib` 的最低需求

`src.plotlib.simulation_heatmaps.load_simulation_arrays()` 目前只要求這些欄位一定存在：

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

這表示：

- 若未來新增 simulation 指標，heatmap 層不一定要立刻改
- 但若更名或刪除上面十個欄位，dashboard simulation plots 會直接壞掉

## `result` 的語意

程式中目前把 unresolved order 視為 `-1`。在 heatmap builder：

- fill probability 圖只會統計 `result != -1` 的樣本
- profit 圖只會統計 `result == 1` 的樣本

這是目前 dashboard 對 simulation 結果的核心假設。
## Profit timing

- `result == 1`: profit is sampled from `fill_time + resolved_time`
- `result == 0`: profit is sampled from `cancel_time + resolved_time`
- `result == -1`: profit remains `NaN`

# Simulation Data Format

## Input naming

simulation 的原始輸入檔命名由 `src.raw_batches` 定義：

- `level2-<product_id>-init-<timestamp>.csv`
- `level2-<product_id>-updates-<timestamp>.csv`
- `trade-<product_id>-<timestamp>.csv`

## Output naming

simulation artifact 命名由 `src.dataset_artifacts` 定義：

```text
<product_id>-<timestamp>-<time_step>-resolved-<resolved_time>-simulation-<algorithm_name>.npz
```

## Metadata keys

- `algorithm`
- `product_id`
- `file_stem`
- `time_step`
- `base_tick`
- `resolved_time`

## Result keys

bid side:

- `bid_prices`
- `bid_near_size`
- `bid_opp_size`
- `bid_survival_time`
- `bid_ahead`
- `bid_behind`
- `bid_vorder_ratio`
- `bid_result`
- `bid_spread`
- `bid_mid_price`
- `bid_micro_price`
- `bid_mid_profit`
- `bid_micro_profit`

ask side:

- `ask_prices`
- `ask_near_size`
- `ask_opp_size`
- `ask_survival_time`
- `ask_ahead`
- `ask_behind`
- `ask_vorder_ratio`
- `ask_result`
- `ask_spread`
- `ask_mid_price`
- `ask_micro_price`
- `ask_mid_profit`
- `ask_micro_profit`

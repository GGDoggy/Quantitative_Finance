# Preprocess Formats and Contracts

## Input contract

`src.preprocess` 的輸入是 `src.raw_batches.RawBatch`。

raw CSV 命名規則由 `src.raw_batches` 定義：

- `level2-<product_id>-init-<timestamp>.csv`
- `level2-<product_id>-updates-<timestamp>.csv`
- `trade-<product_id>-<timestamp>.csv`

## Output contract

preprocessed artifact 命名規則由 `src.dataset_artifacts` 定義：

```text
<product_id>-<timestamp>-<time_step>-orderbook_for_plot.npz
```

## Required persisted keys

orderbook payload 至少要有：

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

trade payload 若存在，至少要有：

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

## Merge contract

所有 builder 寫入同一個 payload dict。

允許：

- 新 key
- 相同 key 且值完全一致

拒絕：

- 相同 key 但值不同

衝突時會拋出 `PreprocessOutputConflictError`。

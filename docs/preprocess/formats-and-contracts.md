# Preprocess Formats And Contracts

本文件描述 `src.preprocess` 寫出的 preprocessed `.npz` 與 `load_preprocessed_payload(...)` 對資料 schema 的要求。

## Artifact 檔名

檔名格式：

```text
{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz
```

範例：

```text
ETH-USD-20240501.120000-0.01-orderbook_for_plot.npz
```

## `.npz` 最低需求

所有 preprocessed dataset 至少要能通過 orderbook schema 驗證，也就是必須包含：

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

`mid` 不是強制欄位。若缺少，`src.plotlib.types.normalize_orderbook_payload_to_v1(...)` 會以 `(bid + ask) / 2` 補出。

如果 dataset 也支援 trade 類 view，則還應包含：

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

另外 preprocess 會寫入：

- `available_views`

## 陣列 shape contract

`load_preprocessed_payload(...)` 目前會驗證：

- `time_axis.ndim == 1`
- `price_axis.ndim == 1`
- `data.ndim == 2`
- `bid.ndim == 1`
- `ask.ndim == 1`
- `bid.shape == ask.shape`
- `data.shape[0] == time_axis.shape[0]`
- `bid.shape[0] == time_axis.shape[0]`
- `ask.shape[0] == time_axis.shape[0]`
- `data.shape[1] == price_axis.shape[0]`

如果任一條件不成立，會丟出 `PreprocessedDataSchemaError`。

## orderbook payload 的語意

- `price_axis`
  - 升冪排列的價格 level
- `time_axis`
  - `datetime64[ns]` 陣列
- `data`
  - shape 為 `(time, price)`
  - 來自 orderbook snapshot 序列
- `bid`
  - 每個 time sample 的最佳 bid 價格
- `ask`
  - 每個 time sample 的最佳 ask 價格
- `mid`
  - 每個 time sample 的中間價，可選

## trade payload 的語意

- `trade_time`
  - `datetime64[ns]` 陣列
- `trade_price`
  - 成交價格
- `trade_volume`
  - 成交量
- `trade_side`
  - 成交方向，renderers 目前依賴其數值符號做分類

## `available_views`

preprocess 會把成功產出的 builder key 寫入 `available_views`。目前可能值：

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

之後 catalog 層若同時發現對應 simulation artifact，才會再把 simulation views 補進 `PreprocessedArtifact.available_views`。

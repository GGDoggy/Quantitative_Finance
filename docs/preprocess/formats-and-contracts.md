# Preprocess Formats And Contracts

這份文件只描述 preprocess 產出的 base dataset contract，也就是 `*-orderbook_for_plot.npz` 需要滿足的欄位與約束。

## 輸出檔名

```text
{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz
```

實際路徑由 `src.dataset_artifacts.build_preprocessed_output_path()` 統一建構。

## 最低必要欄位

所有可被 dashboard 視為有效 preprocessed dataset 的 `.npz` 至少要有：

- `price_axis`
- `time_axis`
- `data`
- `bid`
- `ask`

這五個欄位同時也是 `src.preprocess.catalog._validate_preprocessed_payload_schema()` 的基本驗證條件。

## 可選欄位

目前 preprocess 也會寫入：

- `available_views`
- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

其中 trades 四個欄位可讓同一份 `.npz` 同時支援：

- `trades_scatter`
- `trade_volume_timeline`

## 維度契約

base orderbook payload 必須滿足：

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

## `available_views`

`available_views` 是用來告訴 dashboard 與 `src.plotlib.registry` 這份 dataset 可以支援哪些圖。

目前 base preprocess 會產生的值可能包含：

- `orderbook`
- `trades_scatter`
- `trade_volume_timeline`

若缺少 `available_views`，catalog 仍可透過欄位存在與否重新推斷。

## Trades payload contract

若 dataset 要支援 trades 相關圖，至少要包含：

- `trade_time`
- `trade_price`
- `trade_volume`
- `trade_side`

語意如下：

- `trade_time`
  - `datetime64[ns]` 陣列
- `trade_price`
  - 成交價
- `trade_volume`
  - 成交量
- `trade_side`
  - taker side，dashboard 目前用 `-1.0` 與 `1.0` 來分色

## 變更時必須同步更新的地方

- 欄位 contract 變更
  - `src/preprocess/pipeline.py`
  - `src/preprocess/catalog.py`
  - `src/plotlib/orderbook.py`
  - `src/plotlib/trades.py`
- view key 變更
  - `src/preprocess/pipeline.py`
  - `src/dataset_artifacts/catalog.py`
  - `src/plotlib/registry.py`

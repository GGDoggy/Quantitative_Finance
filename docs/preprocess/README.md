# `src.preprocess`

`src.preprocess` 目前的角色是把 `src.raw_batches.RawBatch` 轉成 dashboard 可直接消費的 preprocessed `.npz`，同時提供 catalog 掃描與 payload 驗證工具。

它不再是舊版那種以 plot module 為中心的分散式流程；現在的核心是：

1. 載入 raw batch
2. 建立 `PreprocessContext`
3. 依 `PLOT_REGISTRY` 執行 builder
4. 合併 payload chunk
5. 寫出單一 `.npz`
6. 用 artifact discovery 回查剛寫出的 dataset

## 主要責任

- preprocess orchestration
- builder registry
- payload chunk merge 與衝突檢查
- preprocessed dataset discovery compatibility wrapper
- preprocessed payload 載入與 schema 驗證

## 主要模組

- `service.py`
  - `build_context(...)`
  - `build_preprocess_context(...)`
  - `preprocess_batch(...)`
  - `preprocess_batches(...)`
- `registry.py`
  - `PLOT_REGISTRY`
  - `PreprocessBuilderSpec`
- `builders/orderbook.py`
  - 重用 `src.preprocess.orderbook.build_orderbook_payload`
- `builders/trades.py`
  - 產出 `trade_time` / `trade_price` / `trade_volume` / `trade_side`
- `datasets.py`
  - 舊 catalog API 的相容包裝
  - `load_preprocessed_payload(...)`
- `exceptions.py`
  - preprocess / payload schema 相關錯誤

## `PLOT_REGISTRY`

目前 registry 只有三個 view key，且只有三組 preprocess payload：

- `orderbook`
  - required keys: `price_axis`, `time_axis`, `data`, `bid`, `ask`
- `trades_scatter`
  - required keys: `trade_time`, `trade_price`, `trade_volume`, `trade_side`
- `trade_volume_timeline`
  - required keys: `trade_time`, `trade_price`, `trade_volume`, `trade_side`

注意：

- `trades_scatter` 和 `trade_volume_timeline` 共用同一個 trade builder
- simulation heatmap 不在 preprocess registry 內，它們來自 `src.simulation` 輸出的另一類 artifact

## 典型流程

```python
from pathlib import Path

from src.preprocess import preprocess_batch
from src.raw_batches import discover_raw_batches

batches = discover_raw_batches(Path("data/v3"))
dataset = preprocess_batch(batches[0], Path("data/preprocessed"))
print(dataset.path)
print(dataset.available_views)
```

## 輸出

preprocess 輸出檔名由 `src.dataset_artifacts.build_preprocessed_output_path(...)` 決定：

```text
{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz
```

`.npz` 內容至少會有：

- `available_views`
- orderbook keys
- 視情況加入 trade keys

## 相關文件

- [formats-and-contracts.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/preprocess/formats-and-contracts.md)
- [module-reference.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/preprocess/module-reference.md)

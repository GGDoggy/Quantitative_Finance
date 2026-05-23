# Docs

這個目錄整理目前 repo 主線流程的文件，內容以現在的 `src/` 與 `gui/dashboard.py` 為準，而不是舊版 `src.plots`、`service.py`、`discovery.py` 等已被重構掉的模組。

## 建議閱讀順序

1. [raw_batches/README.md](raw_batches/README.md)
   說明 `data/v3` 原始 CSV 批次的命名、發現與載入。
2. [preprocess/README.md](preprocess/README.md)
   說明 raw batch 如何轉成 dashboard 可讀取的 preprocessed `.npz`。
3. [dataset_artifacts/README.md](dataset_artifacts/README.md)
   說明 `data/preprocessed` 內 artifact 的命名、catalog 與 view 偵測。
4. [simulation/README.md](simulation/README.md)
   說明 simulation 的 request、演算法與輸出檔。
5. [plotlib/README.md](plotlib/README.md)
   說明 dashboard 讀取 payload 後如何建構各種圖。

## 主線資料流

```text
data/v3/*.csv
  -> src.raw_batches.discover_raw_batches()
  -> src.preprocess.preprocess_batch()
  -> data/preprocessed/*-orderbook_for_plot.npz
  -> src.plotlib / gui.dashboard

data/v3/*.csv
  -> src.raw_batches.discover_raw_batches()
  -> src.simulation.simulate_batch()
  -> data/preprocessed/*-simulation-*.npz
  -> src.dataset_artifacts.discover_preprocessed_artifacts()
  -> src.plotlib / gui.dashboard
```

## 模組對照

- `src.raw_batches`
  - 負責 raw CSV 的 filename parsing、batch discovery、CSV loading。
- `src.preprocess`
  - 負責把 `RawBatch` 轉成 preprocessed orderbook/trades `.npz`。
- `src.dataset_artifacts`
  - 負責 preprocessed / simulation artifact 的命名、解析、catalog 與 view 偵測。
- `src.simulation`
  - 負責 virtual order simulation、平行執行與 simulation `.npz` 寫檔。
- `src.plotlib`
  - 負責把 preprocessed payload 或 simulation arrays 轉成 HoloViews / Plotly 圖。
- `gui/dashboard.py`
  - 把 catalog、preprocess、simulation、plot controls 組成單一 Panel dashboard。

## 維護原則

- 文件內的 public API 以各模組 `__init__.py` 匯出的名稱為主。
- 如果改動檔名規則，至少同步更新：
  - `src/raw_batches/api.py`
  - `src/dataset_artifacts/catalog.py`
  - `docs/raw_batches/README.md`
  - `docs/dataset_artifacts/README.md`
- 如果改動 preprocessed payload key 或 plot 類型，至少同步更新：
  - `src/preprocess/pipeline.py`
  - `src/plotlib/registry.py`
  - `docs/preprocess/formats-and-contracts.md`
  - `docs/plotlib/api.md`

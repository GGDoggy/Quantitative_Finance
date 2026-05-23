# `docs/`

這份文件目錄現在對應 `src/` 的現行模組切分，而不是舊版 `src.plots` / `simulation.service` 架構。

## 對應關係

- [dataset_artifacts/README.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/dataset_artifacts/README.md)
  - `src.dataset_artifacts`
  - artifact 命名、解析、discovery、locator
- [raw_batches/README.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/raw_batches/README.md)
  - `src.raw_batches`
  - `data/v3` 原始 CSV 批次 discovery 與 loading
- [preprocess/README.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/preprocess/README.md)
  - `src.preprocess`
  - raw batch -> preprocessed `.npz`
- [plotlib/README.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/README.md)
  - `src.plotlib`
  - loaders、payload normalization、renderers
- [simulation/README.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/README.md)
  - `src.simulation`
  - simulation request / runner / IO / algorithms

## 目前主流程

```text
data/v3 CSV
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/*-orderbook_for_plot.npz
  -> src.plotlib

data/v3 CSV
  -> src.raw_batches
  -> src.simulation
  -> data/preprocessed/*-simulation-*.npz
  -> src.plotlib
```

## 文件撰寫原則

這批文件以「現在程式碼實際提供什麼 API / contract」為主，不再保留已不存在的舊模組描述。若之後 `src/` 再重構，應優先同步：

- 模組入口 `__init__.py`
- 檔名規則與資料格式
- GUI / dashboard 會依賴的 payload contract

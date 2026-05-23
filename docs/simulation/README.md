# `src.simulation`

`src.simulation` 目前是一個最小但完整的 simulation library。它接受 `RawBatch` 或已載入的 market data，執行指定演算法，最後把結果寫成 `.npz` artifact 供 dashboard heatmap 使用。

## 模組定位

它的設計可拆成四塊：

1. request / result models
2. algorithm registry
3. runner
4. IO 與 artifact 輸出

## 主要 API

- `list_algorithms()`
- `load_raw_dataset(batch)`
- `simulate_loaded_data(data, request)`
- `simulate_batch(batch, request, output_dir)`
- `simulate_batches(batches, request, output_dir)`

## 主要檔案

- `models.py`
  - `LoadedMarketData`
  - `SimulationRequest`
  - `SimulationResult`
  - `SimulationJobResult`
- `registry.py`
  - 演算法名稱到函式的映射
- `runner.py`
  - 單批次與多批次 simulation
- `io.py`
  - raw 載入、輸出檔名、`.npz` 序列化
- `constants.py`
  - 預設路徑與預設參數

## 預設值

- `DATA_V3_PATH = Path("data/v3")`
- `OUTPUT_PATH = Path("data/preprocessed")`
- `DEFAULT_TIME_STEP = 0.01`
- `DEFAULT_BASE_TICK = 0.00000001`
- `DEFAULT_RESOLVED_TIME = 1.0`

## 目前註冊的演算法

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

## 多批次執行

`simulate_batches(...)` 在資料筆數大於 1 時會使用 `ProcessPoolExecutor` 平行化。worker 數量由 `get_default_worker_count(...)` 決定，預設不超過 `os.cpu_count()`。

## 相關文件

- [api.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/api.md)
- [data-format.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/data-format.md)
- [algorithms.md](C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/algorithms.md)

# `src.simulation`

`src.simulation` 提供 raw batch 上的 virtual order simulation。它會把一批 market data 跑過指定演算法，再把輸出寫成 simulation `.npz`，讓 dashboard 畫出 fill probability 與 profit heatmaps。

細節請看：

- [api.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/api.md)
- [algorithms.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/algorithms.md)
- [data-format.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/simulation/data-format.md)

## 主流程

```text
RawBatch
  -> load_raw_dataset()
  -> LoadedMarketData
  -> simulate_loaded_data()
  -> SimulationResult
  -> save_result_file()
  -> data/preprocessed/*-simulation-*.npz
```

## Public API

- `list_algorithms()`
- `load_raw_dataset(dataset)`
- `simulate_loaded_data(data, request)`
- `simulate_batch(dataset, request, output_dir)`
- `simulate_batches(datasets, request, output_dir)`
- `parse_dataset_groups(data_v3_path)`
- `build_output_path(...)`

## 預設常數

- `DEFAULT_TIME_STEP = 0.01`
- `DEFAULT_BASE_TICK = 0.00000001`
- `DEFAULT_RESOLVED_TIME = 1.0`

`gui/dashboard.py` 目前另外使用 `GUI_SIMULATION_BASE_TICK = 0.01`，那是 UI 決策，不是 library 預設。

## 目前支援的演算法

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

## 平行執行

`simulate_batches()` 在 dataset 數量大於 1 時會使用 `ProcessPoolExecutor`，worker 數量由 `get_default_worker_count()` 依 `os.cpu_count()` 與任務數決定。

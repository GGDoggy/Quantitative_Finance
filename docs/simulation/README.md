# `src.simulation`

`src.simulation` 只負責把 `RawBatch` 轉成 simulation `.npz`。

它不再負責：

- raw CSV 批次 discovery 規則
- raw batch identity model 定義
- simulation artifact 命名規則定義

這些職責已移到：

- `src.raw_batches`
- `src.dataset_artifacts`

## Current responsibilities

- 定義 simulation request / result models
- 管理 algorithm registry
- 執行 simulation runner
- 寫出 simulation artifact

## Main APIs

- `list_algorithms()`
- `load_raw_dataset(batch)`
- `simulate_loaded_data(data, request)`
- `simulate_batch(batch, request, output_dir)`
- `simulate_batches(batches, request, output_dir)`

## Flow

1. `src.raw_batches.discover_raw_batches()` 找到 `RawBatch`
2. `src.simulation.load_raw_dataset()` 讀入 market data
3. `src.simulation.simulate_batch()` 執行演算法
4. `src.dataset_artifacts.build_simulation_output_path()` 決定輸出檔名
5. `src.plotlib.loaders.simulation` 讀 simulation arrays 給 heatmap renderers

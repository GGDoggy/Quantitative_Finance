# Simulation API

## `SimulationRequest`

欄位：

- `algorithm`
- `time_step`
- `base_tick`
- `resolved_time`

建構時會驗證：

- `algorithm` 不可為空
- `time_step` 必須是正的有限值
- `base_tick` 必須是正的有限值
- `resolved_time` 必須是非負有限值

## `simulate_loaded_data(data, request)`

最底層的執行入口。它：

1. 從 registry 取出演算法
2. 呼叫演算法函式
3. 把 tuple 輸出包成 `SimulationResult`

適合測試或已自行處理 raw loading 的情境。

## `simulate_batch(dataset, request, output_dir)`

完整單批次流程：

1. 根據 request 計算輸出檔名
2. 載入 `RawBatch`
3. 執行 simulation
4. 寫出 `.npz`
5. 回傳 `SimulationJobResult`

`SimulationJobResult` 欄位：

- `dataset`
- `output_path`
- `overwritten`

其中 `overwritten` 表示正式輸出路徑在本次寫入前是否已存在。

## `simulate_batches(datasets, request, output_dir)`

如果 `len(datasets) <= 1`，直接逐筆呼叫 `simulate_batch(...)`。

如果資料筆數大於 1，則：

- 丟給 process pool 平行跑
- 各 worker 回傳 `SimulationWorkerPayload`
- 主程序再轉回 `SimulationJobResult`
- 最後依輸入 dataset 順序重新排序

如果任何 worker 失敗，會丟出 `RuntimeError("Batch processing failed for: ...")`。

## `list_algorithms()`

回傳當前 registry 已註冊的演算法名稱。

## `load_raw_dataset(dataset)`

把 `RawBatch` 轉成 `LoadedMarketData`：

- `init`
- `updates`
- `trades`
- `start_time`

## `build_output_path(...)`

定義 simulation artifact 路徑，實際委派給 `src.dataset_artifacts.build_simulation_output_path(...)`。

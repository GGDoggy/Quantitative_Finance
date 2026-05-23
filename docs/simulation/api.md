# `src.simulation` API

## Public models

- `RawBatch`
  - 從 `src.raw_batches` 匯入，作為 simulation input identity
- `LoadedMarketData`
- `SimulationRequest`
- `SimulationResult`
- `SimulationJobResult`

## Functions

### `load_raw_dataset(batch: RawBatch) -> LoadedMarketData`

讀入一個 raw batch 的 init / updates / trades。

### `simulate_loaded_data(data, request) -> SimulationResult`

對已載入的 market data 執行指定演算法。

### `simulate_batch(batch, request, output_dir) -> SimulationJobResult`

完整流程：

1. load raw batch
2. run simulation
3. write simulation artifact

### `simulate_batches(batches, request, output_dir) -> list[SimulationJobResult]`

對多個 raw batch 執行 simulation；批次數大於 1 時可走平行流程。

### `list_algorithms() -> list[str]`

回傳 registry 中已註冊的 algorithm 名稱。

# Simulation API

## Public exports

### 函式

- `list_algorithms() -> list[str]`
- `build_output_path(output_path, product_id, timestamp, time_step, algorithm_name, resolved_time) -> Path`
- `parse_dataset_groups(data_v3_path) -> list[RawBatch]`
- `load_raw_dataset(dataset: RawBatch) -> LoadedMarketData`
- `simulate_loaded_data(data: LoadedMarketData, request: SimulationRequest) -> SimulationResult`
- `simulate_batch(dataset: RawBatch, request: SimulationRequest, output_dir) -> SimulationJobResult`
- `simulate_batches(datasets: list[RawBatch], request: SimulationRequest, output_dir) -> list[SimulationJobResult]`

### 資料模型

- `LoadedMarketData`
- `SimulationRequest`
- `SimulationResult`
- `SimulationJobResult`

## `SimulationRequest`

欄位：

- `algorithm`
- `time_step`
- `base_tick`
- `resolved_time`
- `order_depth`（預設 `1`）

驗證規則：

- `algorithm` 不可為空
- `time_step` 必須是正的有限值
- `base_tick` 必須是正的有限值
- `resolved_time` 必須是非負有限值
- `order_depth` 必須是正整數；`1` 保持既有 best-only 模擬，相容既有輸出與測試

## `SimulationResult`

這個 model 封裝演算法輸出的所有 numpy arrays。主要欄位分成 bid / ask 兩側：

- size 與價格
  - `bid_prices`, `ask_prices`
  - `bid_near_size`, `ask_near_size`
  - `bid_opp_size`, `ask_opp_size`
  - `bid_spread`, `ask_spread`
- queue 狀態
  - `bid_ahead`, `ask_ahead`
  - `bid_behind`, `ask_behind`
  - `bid_vorder_ratio`, `ask_vorder_ratio`
  - `bid_survival_time`, `ask_survival_time`
- fill 結果
  - `bid_result`, `ask_result`
- profit
  - `bid_mid_profit`, `ask_mid_profit`
  - `bid_micro_profit`, `ask_micro_profit`
  - `bid_mid_price`, `ask_mid_price`
  - `bid_micro_price`, `ask_micro_price`

## `SimulationJobResult`

- `dataset`
- `output_path`
- `overwritten`

`overwritten` 可讓 UI 知道這次寫檔是否覆蓋了既有 simulation artifact。

## 例子

```python
from pathlib import Path

from src.raw_batches import discover_raw_batches
from src.simulation import (
    DEFAULT_BASE_TICK,
    DEFAULT_RESOLVED_TIME,
    DEFAULT_TIME_STEP,
    SimulationRequest,
    simulate_batch,
)

batches = discover_raw_batches(Path("data/v3"))
request = SimulationRequest(
    algorithm="event_balanced",
    time_step=DEFAULT_TIME_STEP,
    base_tick=DEFAULT_BASE_TICK,
    resolved_time=DEFAULT_RESOLVED_TIME,
    order_depth=1,
)
result = simulate_batch(batches[0], request, Path("data/preprocessed"))
print(result.output_path)
```

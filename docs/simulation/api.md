# `src/simulation` API 參考

本頁聚焦目前對外可用的 API，以及內部常用但值得理解的 helper 入口。

## Public API

`src/simulation/__init__.py` 目前對外 re-export：

- `list_algorithms`
- `load_raw_dataset`
- `simulate_loaded_data`
- `simulate_batch`
- `simulate_batches`
- `LoadedMarketData`
- `RawSimulationDataset`
- `SimulationJobResult`
- `SimulationRequest`
- `SimulationResult`

## Data Models

### `RawSimulationDataset`

表示一個可執行 simulation 的原始批次。

欄位：

- `product_id: str`
- `timestamp: str`
- `file_stem: str`
- `init_path: Path`
- `updates_path: Path`
- `trade_path: Path`

用途：

- 作為 raw dataset 的最小識別單位
- 作為輸出檔名與 metadata 的來源

### `LoadedMarketData`

表示已從 CSV 讀入記憶體的資料。

欄位：

- `init: list[list[float]]`
- `updates: list[list[float]]`
- `trades: list[list[float]]`
- `start_time: float`

注意：

- 目前保留原始 list-of-list 結構，沒有額外包成 dataframe 或 ndarray schema class
- `start_time` 來自檔名 timestamp，會被轉成 Unix time

### `SimulationRequest`

simulation 參數容器。

欄位：

- `algorithm: str`
- `time_step: float`
- `base_tick: float`
- `resolved_time: float`

驗證規則：

- `algorithm` 不能為空
- `time_step` 必須是正的有限值
- `base_tick` 必須是正的有限值
- `resolved_time` 必須是非負有限值

### `SimulationResult`

演算法輸出的標準化結果容器。內含 26 個 `numpy.ndarray` 欄位，分成四組：

#### bid queue / fill 特徵

- `bid_prices`
- `bid_near_size`
- `bid_opp_size`
- `bid_survival_time`
- `bid_ahead`
- `bid_behind`
- `bid_vorder_ratio`
- `bid_result`
- `bid_spread`

#### ask queue / fill 特徵

- `ask_prices`
- `ask_near_size`
- `ask_opp_size`
- `ask_survival_time`
- `ask_ahead`
- `ask_behind`
- `ask_vorder_ratio`
- `ask_result`
- `ask_spread`

#### bid resolved-time 衍生指標

- `bid_mid_price`
- `bid_micro_price`
- `bid_mid_profit`
- `bid_micro_profit`

#### ask resolved-time 衍生指標

- `ask_mid_price`
- `ask_micro_price`
- `ask_mid_profit`
- `ask_micro_profit`

輔助方法：

- `from_algorithm_output(values)`：把演算法 tuple 包成 dataclass
- `as_tuple()`：依固定順序輸出 tuple，供 `.npz` 序列化使用

### `SimulationJobResult`

批次執行結果摘要。

欄位：

- `dataset: RawSimulationDataset`
- `output_path: Path`
- `overwritten: bool`

`overwritten=True` 表示目標輸出檔在執行前已存在。

## Functions

### `list_algorithms() -> list[str]`

回傳 registry 內已註冊的演算法名稱。UI 下拉選單與其他上游邏輯應該以它為準，不要手寫字串常數。

### `load_raw_dataset(dataset: RawSimulationDataset) -> LoadedMarketData`

從單一 raw dataset 讀入：

- init CSV
- updates CSV
- trade CSV

這個函式不做高層 orchestration，只做 I/O 與 timestamp 轉換。

### `simulate_loaded_data(data: LoadedMarketData, request: SimulationRequest) -> SimulationResult`

最純的 library 執行入口。適合：

- 已經把資料 preload 到記憶體
- 想直接對某演算法做單次執行
- 不想碰輸出檔案

### `simulate_batch(dataset: RawSimulationDataset, request: SimulationRequest, output_dir: Path | str) -> SimulationJobResult`

單一 dataset 的完整流程入口。會：

1. 讀取 raw CSV
2. 執行 simulation
3. 把結果存成 `.npz`
4. 回傳結果摘要

### `simulate_batches(datasets: list[RawSimulationDataset], request: SimulationRequest, output_dir: Path | str) -> list[SimulationJobResult]`

多 dataset orchestration。

行為：

- `0` 或 `1` 個 dataset 時，走 serial path
- `2` 個以上時，走 `ProcessPoolExecutor`
- 回傳順序會被重排回原始 `datasets` 順序

## `io.py` 內值得知道的內部 API

### `parse_dataset_groups(data_v3_path)`

掃描 v3 CSV 目錄並回傳所有完整的 `RawSimulationDataset`。dashboard 或未來 CLI 若要列出可模擬批次，通常應該先從這裡開始。

### `build_output_path(...)`

建立 simulation 輸出檔名：

```text
<product_id>-<timestamp>-<time_step>-resolved-<resolved_time>-simulation-<algorithm>.npz
```

這個命名規則與 catalog/plot discovery 強耦合。

### `save_result_file(...)`

把 metadata 與 `SimulationResult` 內容壓縮寫入 `.npz`。

## Constants

定義於 `constants.py`：

- `DATA_V3_PATH = Path("data/v3")`
- `OUTPUT_PATH = Path("data/preprocessed")`
- `DEFAULT_TIME_STEP = 0.01`
- `DEFAULT_BASE_TICK = 0.00000001`
- `DEFAULT_RESOLVED_TIME = 1.0`

## 最小使用範例

```python
from src.simulation import (
    SimulationRequest,
    list_algorithms,
    simulate_batch,
)
from src.simulation.io import parse_dataset_groups

datasets = parse_dataset_groups("data/v3")
request = SimulationRequest(
    algorithm=list_algorithms()[0],
    time_step=0.01,
    base_tick=1e-8,
    resolved_time=1.0,
)

result = simulate_batch(
    dataset=datasets[0],
    request=request,
    output_dir="data/preprocessed",
)

print(result.output_path)
```

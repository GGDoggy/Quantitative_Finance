# Simulation 模組重構變更說明

## 背景
本次調整目標是把 `src/simulation/` 的演算法模組拆成「對外介面」與「內部共用實作」，避免其他內部程式直接依賴某個特定演算法檔案。

## 主要改動
- 新增 `src/simulation/_simulation_core.py`
  - 放置原本 `time_averaged_random_cancellation.py` 內部共用的核心資料結構、CSV/時間解析工具與共用 reconciliation 邏輯。
- `src/simulation/time_averaged_random_cancellation.py`
  - 改成對外介面 wrapper，只保留 `ALGORITHM_NAME` 與 `simulate_virtual_best_orders` 匯出。
- 新增 `src/simulation/algorithm_helpers.py`
  - 抽出 `event_balanced` 與 `best_size_changed` 共用小工具，避免演算法之間彼此 import。
- `src/simulation/event_balanced.py`
  - 改為依賴 `_simulation_core.py` 與 `algorithm_helpers.py`，不再作為其他演算法的工具來源。
- `src/simulation/best_size_changed.py`
  - 移除對 `event_balanced.py` 的內部 helper 依賴，改依賴 `algorithm_helpers.py`。
- `src/simulation/library.py`
  - 讀檔與時間解析改由 `_simulation_core.py` 提供；演算法名稱與執行函式維持原本對外名稱。

## 對外呼叫方式影響

### 原本使用方式
1. 直接使用演算法（time averaged）
```python
from src.simulation.time_averaged_random_cancellation import simulate_virtual_best_orders
```
2. 直接使用演算法（event balanced）
```python
from src.simulation.event_balanced import simulate_virtual_best_orders
```
3. 直接使用演算法（best size changed）
```python
from src.simulation.best_size_changed import simulate_virtual_best_orders
```
4. 透過 library 名稱分派
```python
from src.simulation.library import get_algorithm
algo = get_algorithm("time_averaged_random_cancellation")
```

### 更改後使用方式
> 對外演算法入口 **不變**，上述 1~4 仍可使用。

建議使用：
1. 直接使用演算法（保持不變）
```python
from src.simulation.time_averaged_random_cancellation import simulate_virtual_best_orders
from src.simulation.event_balanced import simulate_virtual_best_orders
from src.simulation.best_size_changed import simulate_virtual_best_orders
```
2. 使用 library 分派（保持不變）
```python
from src.simulation.library import get_algorithm
algo = get_algorithm("time_averaged_random_cancellation")
```

### 不建議/已調整的內部用法
- 不要再讓內部程式互相從演算法模組拉 helper：
  - `best_size_changed.py` 不再從 `event_balanced.py` import helper。
  - `event_balanced.py` 與 `best_size_changed.py` 不再從 `time_averaged_random_cancellation.py` 拉內部工具。
- 內部共用工具請改用：
  - `src/simulation/_simulation_core.py`
  - `src/simulation/algorithm_helpers.py`

# Simulation Algorithms

## Registry

`src.simulation.registry.ALGORITHMS` 目前註冊三個演算法：

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

它們都遵守相同函式介面：

```python
simulate_virtual_best_orders(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
    resolved_time,
)
```

並回傳可被 `SimulationResult.from_algorithm_output(...)` 接收的 tuple。

## `time_averaged_random_cancellation`

- 實作位於 `src/simulation/_simulation_core.py`
- `src/simulation/time_averaged_random_cancellation.py` 只是公開名稱與轉出函式

這是目前最底層、最核心的實作來源，其他演算法也大量重用 `_simulation_core.py` 內的 helper。

## `event_balanced`

- 實作位於 `src/simulation/event_balanced.py`
- 維持單一 active bid / ask virtual order 的平衡式流程
- 會在事件推進中根據 top-of-book 演化更新 active order 狀態

## `best_size_changed`

- 實作位於 `src/simulation/best_size_changed.py`
- 在最佳價或最佳量發生變化時傾向建立新的 virtual order
- 內部會追蹤 unresolved order 數量與對應 evidence

## 共用核心

`_simulation_core.py` 負責大部分底層機制，包括：

- orderbook 更新
- best bid / ask index 維護
- event stream 建立
- trade evidence 累積與拆分
- order reconcile
- unresolved order finalize
- evolved quote / profit 計算

這代表新增演算法時，通常不需要重寫整個 orderbook event engine，而是重組：

- 何時 submit virtual order
- 何時替換 active order
- 如何解讀 best quote 變化

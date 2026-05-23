# Simulation Algorithms

目前 `src.simulation.algorithms` 註冊三個演算法：

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

它們都必須符合同一個呼叫介面：

```python
algorithm(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
    resolved_time,
)
```

並回傳可被 `SimulationResult.from_algorithm_output()` 接受的 tuple。

## `time_averaged_random_cancellation`

- 目前是 core 中的 `simulate_virtual_best_orders` 別名
- 可視為 baseline 演算法
- 以時間平均取消邏輯模擬 best quote 上的虛擬掛單

## `event_balanced`

- 維持 bid / ask 各一個 active virtual order
- 在 orderbook update 與 trade evidence 流中持續 reconcile
- 比較偏向事件驅動的平衡追蹤

## `best_size_changed`

- 當最佳 bid 或 ask 的價格或 size 發生變化時，會嘗試新增新的虛擬掛單
- 比 `event_balanced` 更直接依最佳檔位變化觸發 submit

## 共通行為

三個演算法都建立在 `src.simulation.core` 內的共用工具之上，例如：

- event stream 建構
- best bid / ask index 維護
- queue reconciliation
- unresolved order finalize
- quote timeline 補齊

因此大部分 contract 改動應優先檢查 `core.py`，不是只改單一演算法函式。

## 新增演算法時的最低工作

1. 實作符合既有函式簽名的演算法
2. 把名稱加入 `ALGORITHMS`
3. 確認輸出 tuple 的欄位順序與 `SimulationResult` 一致
4. 確認 `list_algorithms()` 可以讓 dashboard 自動看到新選項

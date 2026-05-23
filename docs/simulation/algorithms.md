# Simulation 演算法說明

目前 `src/simulation/registry.py` 註冊了三種演算法。三者都共享同一組輸出 schema，但「何時提交虛擬單」與「同一側是否允許多筆未解決單並存」不同。

## 共同前提

三個演算法都建立在相同的基礎假設上：

- 只模擬 best bid / best ask 上的虛擬掛單
- 原始資料來自單一 batch 的：
  - level2 init
  - level2 updates
  - trades
- 模擬區間使用 orderbook 與 trades 的時間交集，並額外做：
  - `simulation_start = max(orderbook_start_time, trade_start_time) + 1.0`
  - `simulation_end = min(orderbook_end_time, trade_end_time) - 1.0`
- 若沒有 trades，或可模擬區間為空，直接回傳空結果

## 共用核心能力

下列能力主要在 `_simulation_core.py` 中實作，演算法模組只是套用不同的提交策略：

- order book 更新與 best price 推進
- trade evidence 累積
- queue ahead / behind 推進
- 價格變動時的 fill / non-fill 判定
- unresolved order 在 `resolved_time` 視角下的 mid/micro price 與 profit 計算

## 1. `time_averaged_random_cancellation`

檔案：

- [`src/simulation/time_averaged_random_cancellation.py`](../../src/simulation/time_averaged_random_cancellation.py)
- 實作實際上直接沿用 [`src/simulation/_simulation_core.py`](../../src/simulation/_simulation_core.py) 的 `simulate_virtual_best_orders`

### 核心行為

- 依固定 `time_step` 週期提交新的 bid / ask 虛擬單
- 只要還在 `simulation_end` 之前，就會持續定時提交
- 同一價格層可以累積多筆 unresolved order

### 適合的理解方式

這個演算法比較像「時間平均抽樣」：

- 不要求 best quote 發生變化才提交
- 可以在平靜市場中持續產生樣本
- 對 `time_step` 參數最敏感

### 主要優點

- 樣本生成規則穩定
- 比較容易控制抽樣頻率
- 對不同資料批次較容易做橫向比較

### 主要限制

- 若市場在某段時間幾乎不動，仍會機械式提交虛擬單
- 樣本彼此時間相關性可能較高

## 2. `event_balanced`

檔案：

- [`src/simulation/event_balanced.py`](../../src/simulation/event_balanced.py)

### 核心行為

- 初始化時先在 `simulation_start` 嘗試提交
- 之後只有在 event 推進後，且某一側沒有 active unresolved order 時，才補一張新的虛擬單
- bid 與 ask 各自最多維持一張 active order

### 直觀理解

它更像是「事件平衡抽樣」：

- 每側同一時間只追一張代表性虛擬單
- 一旦該單已 resolve，下一次合適事件才會重新補單

### 主要優點

- 降低同側樣本互相重疊的程度
- 比固定時間輪詢更貼近事件驅動

### 主要限制

- 樣本數通常少於 time-averaged
- 在高頻變動段落，補單時點依賴事件序列而不是固定時鐘

## 3. `best_size_changed`

檔案：

- [`src/simulation/best_size_changed.py`](../../src/simulation/best_size_changed.py)

### 核心行為

- 初始化時先在 `simulation_start` 嘗試提交
- 後續只有在 best bid 或 best ask 的「價格或 size」發生變化時，才針對該側提交新虛擬單
- 同一側可以累積多筆 unresolved order

### 與 `event_balanced` 的關鍵差異

- `event_balanced` 偏向每側維持單一 active order
- `best_size_changed` 則是在 top-of-book 狀態改變時留下新的觀測樣本

### 適合的理解方式

這個演算法比較像「狀態轉換抽樣」：

- 樣本與 top-of-book regime change 綁定
- 若 best level 長時間不變，新增樣本會顯著減少

### 主要優點

- 樣本與 book 狀態變化更直接對齊
- 比 purely time-based 抽樣更有事件意義

### 主要限制

- 樣本數高度依賴市場活躍度
- 同一側可累積多筆 unresolved order，解讀時要留意樣本相關性

## 演算法比較

| 演算法 | 提交觸發 | 同側 active order 數 | 對 `time_step` 依賴 |
| - | - | - | - |
| `time_averaged_random_cancellation` | 固定時間間隔 | 可多筆 | 高 |
| `event_balanced` | 事件後補單 | 每側最多 1 筆 active | 低，主要只影響初始提交 |
| `best_size_changed` | best price 或 best size 改變 | 可多筆 | 低，主要只影響初始提交 |

## 如何新增新演算法

最小需求有三個：

1. 新檔案提供 `ALGORITHM_NAME`
2. 新檔案提供與既有演算法相同簽名的 callable
3. 回傳 tuple 順序必須與 `SimulationResult` 完全一致

之後再到 `registry.py` 新增對應：

```python
ALGORITHMS = {
    "...": simulate_virtual_best_orders,
}
```

若新演算法輸出 schema 與現有 26 欄不同，則不能直接接入目前 plot 與 catalog 流程。

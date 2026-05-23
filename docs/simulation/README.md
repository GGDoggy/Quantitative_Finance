# `src/simulation` 文檔

這份文檔描述目前 `src/simulation/` 的實際結構、資料流、公開 API 與演算法差異。內容以現有程式碼為準，而不是舊版腳本或過時 README 片段。

## 適用範圍

`src/simulation` 是一個 library module，負責把 `data/v3` 的原始 CSV 批次資料轉成 simulation `.npz`，供下列兩類消費者使用：

- `gui/` 中的 Panel dashboard
- `src/plots/` 中的 fill probability / profit heatmap

它本身目前不提供正式 CLI entrypoint，也不直接處理 UI 狀態。

## 你應該先看哪幾個檔案

- [`src/simulation/__init__.py`](../../src/simulation/__init__.py)
  - public API re-export
- [`src/simulation/models.py`](../../src/simulation/models.py)
  - request / result / dataset data model
- [`src/simulation/io.py`](../../src/simulation/io.py)
  - raw dataset 掃描、讀取、輸出檔名與 `.npz` 寫入
- [`src/simulation/runner.py`](../../src/simulation/runner.py)
  - 單批次與多批次 orchestration，含平行處理
- [`src/simulation/registry.py`](../../src/simulation/registry.py)
  - 演算法註冊點
- [`src/simulation/_simulation_core.py`](../../src/simulation/_simulation_core.py)
  - 核心撮合/queue 推進邏輯與預設演算法

## 模組分工

### 1. 輸入資料分組與讀取

`io.parse_dataset_groups(data_v3_path)` 會從 `data/v3` 風格的 CSV 目錄中找出完整批次，一個可模擬的批次必須同時具備：

- `level2-<product>-init-<timestamp>.csv`
- `level2-<product>-updates-<timestamp>.csv`
- `trade-<product>-<timestamp>.csv`

只要三者缺一，就不會被視為可模擬 dataset。

### 2. 請求封裝

`SimulationRequest` 負責攜帶 simulation 參數：

- `algorithm`
- `time_step`
- `base_tick`
- `resolved_time`

其中資料驗證在 `__post_init__` 內完成，會拒絕空字串、非有限值、負值或不合理參數。

### 3. 演算法選擇

`registry.ALGORITHMS` 是唯一的演算法查找來源。`runner` 不直接 import 某個演算法名稱，而是透過 `get_algorithm()` 取得 callable。

### 4. 執行與序列化

`runner.simulate_batch()` 的流程是：

1. 依 request 與 dataset 建立輸出檔名
2. 讀取 raw CSV
3. 執行演算法
4. 序列化成 `.npz`
5. 回傳 `SimulationJobResult`

`runner.simulate_batches()` 在 dataset 數量大於 1 時，會自動切到 `ProcessPoolExecutor` 平行執行。

## 典型資料流

```text
data/v3/*.csv
  -> io.parse_dataset_groups()
  -> RawSimulationDataset
  -> io.load_raw_dataset()
  -> LoadedMarketData
  -> runner.simulate_loaded_data()
  -> registry.get_algorithm()
  -> algorithm callable
  -> SimulationResult
  -> io.save_result_file()
  -> data/preprocessed/*simulation*.npz
```

## 輸出結果的核心語意

每次 simulation 會同時產出 bid 與 ask 兩側虛擬單的觀測結果。對每筆虛擬單，至少會有：

- 掛單價格與掛單當下 top-of-book 狀態
- queue 位置估計
- 是否成交 / 未成交 / 尚未 resolve
- 存活時間
- 於 `resolved_time` 視角下計算的 mid / micro price 與 profit

`result` 欄位目前的語意是：

- `1`: fill
- `0`: resolved but not filled
- `-1`: unresolved

實務上 plot 端通常會先過濾 `result != -1` 再畫 fill probability。

## 演算法家族

目前 registry 內有三種演算法：

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

它們都回傳相同 shape 與欄位集合，因此可以共用同一組 `.npz` schema 與下游 plot。

更細的行為差異見 [algorithms.md](./algorithms.md)。

## 與其他模組的關係

### 與 `gui/` 的關係

dashboard 使用 `src.simulation` 來：

- 列出可用演算法
- 接收使用者指定的 `resolved_time` / `time_step`
- 執行 simulation
- 刷新 catalog 後把輸出 `.npz` 交給 plot 模組

### 與 `src/preprocess/catalog.py` 的關係

simulation 輸出檔名會被 catalog 以 regex 解譯；因此檔名規則不是只有 cosmetic，而是資料管線契約的一部分。

### 與 `src/plots/` 的關係

`fill_probability.py`、`profit_heatmap.py`、`cost_fill_probability.py` 都直接讀取 simulation `.npz` 的固定 key。

## 維護時最容易踩到的點

- 改輸出檔名格式時，要同步檢查 `src/preprocess/catalog.py` 與 `src/plots/discovery.py`
- 改 `.npz` key 名稱時，要同步檢查所有 plot loader
- 新增演算法時，必須保證輸出 tuple 順序與既有 schema 完全一致
- `simulate_batches()` 使用 process pool，演算法 callable 與 request/dataset payload 必須保持可 picklable
- 專案目前沒有正式 CLI；如果新增 CLI，應避免把 UI 假設直接塞回 `src/simulation`

## 文檔導覽

- [API 參考](./api.md)
- [演算法說明](./algorithms.md)
- [資料格式與輸出 schema](./data-format.md)

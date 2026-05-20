# 專案摘要

這是一個以 Coinbase 市場資料為來源的量化金融研究專案，現在的 repo 已經從單純的收資料與畫圖腳本，演進成「資料收集 + 預處理 catalog + 互動式儀表板 + simulation」的組合。主要流程如下:

1. `server/websocket.py` 長時間訂閱 websocket，收集 `heartbeats`、`level2` 與 `market_trades`，輸出 `data/v3` 管線使用的 CSV 批次格式。
2. `src/preprocess/` 掃描原始批次、辨識可用資料集、把 `data/v3` 的 CSV 轉成 `data/preprocessed/*.npz`。
3. `src/simulation/` 針對原始批次執行掛單 fill probability / profit 相關 simulation，輸出 simulation `.npz`。
4. `gui/plot.py` 啟動 Panel dashboard，整合資料選擇、raw batch preprocessing、simulation 與互動式視覺化。

`README.md` 仍保留 `data/v1`、`data/v2`、`data/v3` 三種資料格式說明，但目前主線流程是 `v3 CSV -> preprocessed npz / simulation npz -> dashboard plots`。

# 目錄結構

- `server/`
  - `websocket.py`: 主資料收集腳本。會驗證 `sequence_num` 與 heartbeat 連續性，若異常就重啟訂閱。
  - `config.json`: 目前設定 `saving_interval=300` 秒，且只支援單一 `product_id`，預設是 `ETH-USD`。
- `gui/`
  - `plot.py`: 目前唯一的 GUI 入口。提供產品/資料集選擇、raw data 目錄切換、preprocess、simulation 與 plot rendering。
  - `dashboard_settings.json`: 儀表板設定檔；若存在，會保存 simulation heatmap 相關參數。
- `src/preprocess/`
  - `catalog.py`: 掃描 `data/v3` CSV 與 `data/preprocessed` 的 `.npz`，建立 raw batch 與 preprocessed dataset catalog。
  - `service.py`: 執行 preprocess，將單一 raw batch 輸出成 dashboard 可讀取的 `.npz`。
  - `orderbook.py`、`trades_scatter.py`、`trade_volume_timeline.py`: 各 plot 類型對應的 preprocess payload builder。
- `src/plots/`
  - `registry.py`: plot registry，目前已註冊 `Orderbook`、`Trades Scatter`、`Trade Volume Timeline`、`Fill Probability`、`Mid Profit`、`Micro Profit` 與兩種 cost-filtered fill probability heatmap。
  - 其他模組負責實際 plot 建構，混合使用 `holoviews`/`datashader` 與 `plotly`。
- `src/simulation/`
  - `service.py`: 提供 UI-friendly simulation 執行流程。
  - `library.py`: simulation dataset parsing、輸出命名、平行執行等共用邏輯。
  - `best_size_changed.py`、`event_balanced.py`、`time_averaged_random_cancellation.py`: 目前 repo 內的 simulation 演算法實作。
- `fig/`
  - `plot_param.json`: 舊版靜態繪圖參數。
  - `v1/...`: 舊版輸出的靜態 order book PNG。
- `test/`
  - `run_simulation.py`: CLI 式 simulation 測試/操作腳本，可手動挑選 `data/v3` 批次並執行 simulation。
  - `plot_fill_prob.py`: 讀取 simulation `.npz`，用 `matplotlib` 畫 fill probability / sample count heatmap。
- `Assignment/`
  - `Assignment1.ipynb`: 獨立 notebook，應屬課業或分析草稿，未與主流程整合。
- `data/`
  - 目前可見子目錄: `v1/`、`v2/`、`v3/`、`preprocessed/`。
  - `v1` 是舊版 snapshot-only JSON。
  - `v2` 是較早期的 level2 / trade JSON 分段資料。
  - `v3` 是目前主線使用的單商品 CSV 批次格式，檔名由 product 與 UTC timestamp 組成。
  - `preprocessed` 目前同時存放 orderbook plot 用的 `.npz` 與 simulation 輸出的 `.npz`。

# 執行與行為

- 收資料:
  - 依 `README.md`，`websocket.py` 應以 `server/` 為工作目錄執行。
  - 腳本會把 `level2-...csv` 與 `trade-...csv` 寫到當前工作目錄，而不是自動寫進 `data/`。
- 預處理:
  - 已沒有獨立的 `gui/preprocess.py`。
  - 目前 preprocess 由 `src.preprocess.service` 執行，預設 `time_step = 0.01` 秒。
  - `gui/plot.py` 內建 raw batch catalog 與 preprocess 按鈕，可直接把 raw CSV 批次轉成 `.npz`。
- Simulation:
  - `gui/plot.py` 可直接選 raw batch 執行 simulation。
  - simulation 預設會把結果寫到 `data/preprocessed/`，檔名包含 `simulation`、演算法名稱與可選的 `resolved_time`。
  - `test/run_simulation.py` 也能在終端互動式執行 simulation。
- 視覺化:
  - `gui/plot.py` 不再是只看單一硬編碼 dataset 的腳本，而是完整 dashboard。
  - dashboard 預設 raw data 目錄是 `data/v3`，preprocessed 目錄是 `data/preprocessed`，但 raw data 路徑可在 UI 中切換。
  - 啟動後會用 `pn.serve(..., show=True)` 開本地服務與瀏覽器視窗。
  - 可渲染的圖表類型由 `src.plots.registry.PLOT_REGISTRY` 決定。

# 依賴現況

`requirements.txt` 目前列出:

- `aiocsv`
- `aiofiles`
- `bokeh`
- `coinbase_advanced_py==1.8.2`
- `datashader`
- `holoviews`
- `matplotlib==3.10.8`
- `numpy`
- `pandas`
- `panel`
- `plotly`

# 重要注意事項

- `server/websocket.py` 目前假設一次只追一個商品，多商品會直接停止。
- `server/websocket.py` 的輸出檔名不含資料夾路徑，執行位置會直接影響檔案落點。
- `gui/plot.py` 雖然已模組化不少邏輯，但仍屬研究/內部工具型 dashboard，不是成熟的可配置 CLI 或 package entrypoint。
- `data/preprocessed/` 目前混放兩類輸出: plot 用 orderbook `.npz` 與 simulation `.npz`；改資料流程時要注意檔名規則與 catalog 邏輯。
- `src.preprocess.catalog` 透過檔名 regex 判斷資料類型，若調整命名規則，preprocess 與 dashboard catalog 會一起受影響。
- `src.plots.registry` 是目前 preprocess 能否產生 payload、dashboard 能否顯示 plot 的核心註冊點；新增/移除圖表通常要同步更新這裡。
- 專案中仍保留 `data/v1`、`data/v2`、`fig/v1` 與 `Assignment/` 等舊資料或實驗產物，修改主流程時不要誤把它們當成目前 production pipeline。

# 專案摘要

這是一個以 Coinbase 市場資料為來源的量化金融資料收集與視覺化專案，主流程分成三段:

1. `server/websocket.py` 長時間訂閱 websocket，收集 `heartbeats`、`level2` 與 `market_trades`。
2. `gui/preprocess.py` 將 `data/v3` 的原始 CSV 轉成繪圖用的壓縮 `npz`。
3. `gui/plot.py` 讀取 `data/preprocessed`，用 `holoviews`、`datashader`、`panel` 啟動互動式 order book 檢視器。

`README.md` 也記錄了 `data/v1`、`data/v2`、`data/v3` 三種資料格式的設計。

# 目錄結構

- `server/`
  - `websocket.py`: 主資料收集腳本。會驗證 `sequence_num` 與 heartbeat 連續性，若異常就重啟訂閱。
  - `config.json`: 目前設定 `saving_interval=300` 秒，且只支援單一 `product_id`，預設是 `ETH-USD`。
- `gui/`
  - `preprocess.py`: 掃描 `data/v3/`，找出成對的 `level2 init`、`level2 updates`、`trade` 檔，生成 `data/preprocessed/*.npz`。
  - `plot.py`: 載入預處理資料，將委買委賣深度轉成 heatmap，並用 `panel` 啟動本地互動式視覺化。
- `fig/`
  - `plot_param.json`: 舊版繪圖參數。
  - `v1/...`: 已輸出的靜態 order book PNG。
- `test/`
  - `plot_v1.py`: 讀 `data/v1/*.json`，用 `matplotlib` 產生單張柱狀圖。
  - `plot_v2.py`: 讀 `data/v2/*.json`，輸出 `mp4` 動畫；這是實驗性腳本，不是主流程。
- `Assignment/`
  - `Assignment1.ipynb`: 獨立 notebook，應屬課業或分析草稿，未與主流程整合。
- `data/`
  - 僅掃描了結構，未讀內容。
  - 目前可見子目錄: `v1/`、`v2/`、`v3/`、`preprocessed/`、`temp/`。
  - `v1` 主要是 10 秒快照 JSON。
  - `v2` 是較細的 level2 / trade JSON 分段資料。
  - `v3` 是單商品 CSV 格式。
  - `preprocessed` 是 `preprocess.py` 輸出的 `.npz`。
  - `temp` 看起來是 websocket 收集階段產生的中繼 CSV。

# 執行與行為

- 收資料:
  - 依 `README.md`，`websocket.py` 應以 `server/` 為工作目錄執行。
  - 腳本會把 `level2-...csv` 與 `trade-...csv` 寫到當前工作目錄，而不是自動寫進 `data/`。
- 預處理:
  - `gui/preprocess.py` 目前硬編碼讀 `data/v3/`，輸出到 `data/preprocessed/`。
  - 預設 `time_step = 0.01` 秒。
- 視覺化:
  - `gui/plot.py` 目前硬編碼商品 `id = "ETH-USD"`，並只取掃描到的第一個符合檔案。
  - 啟動後會用 `pn.serve(..., show=True)` 開本地服務與瀏覽器視窗。
- Python 環境:
  - 這個專案的所有 Python 程式應在 conda 環境 `quantitative_finance` 下執行。
  - 啟動方式優先使用 `conda run -n quantitative_finance ...`，避免誤用 base 或其他環境。

# 依賴現況

`requirements.txt` 目前只列出:

- `coinbase_advanced_py==1.8.2`
- `matplotlib==3.10.8`

但實際程式還使用了下列套件，尚未寫進 `requirements.txt`:

- `numpy`
- `pandas`
- `datashader`
- `holoviews`
- `panel`
- `aiofiles`
- `aiocsv`

# 重要注意事項

- `server/websocket.py` 目前假設一次只追一個商品，多商品會直接停止。
- `server/websocket.py` 的輸出檔名不含資料夾路徑，執行位置會直接影響檔案落點。
- `gui/plot.py` 與 `gui/preprocess.py` 都有多個硬編碼路徑與參數，較像研究腳本，不是可配置 CLI。
- `test/plot_v1.py` 內有明顯的 f-string 引號問題，檔案目前看起來不能直接執行。
- 專案中存在不少產出檔與資料檔，後續若要重構，應先區分「原始資料」、「中繼資料」與「輸出圖檔」。

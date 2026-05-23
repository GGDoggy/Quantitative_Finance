# Simulation 資料格式

本頁記錄 `src/simulation` 目前吃進去的 raw data 形狀，以及寫出去的 `.npz` schema。

## 輸入資料格式

`parse_dataset_groups()` 預期目錄中存在 v3 CSV，命名如下：

- `level2-<product_id>-init-<timestamp>.csv`
- `level2-<product_id>-updates-<timestamp>.csv`
- `trade-<product_id>-<timestamp>.csv`

其中 `<timestamp>` 目前使用：

```text
YYYYMMDD.HHMMSS
```

例如：

```text
level2-ETH-USD-init-20240501.120000.csv
level2-ETH-USD-updates-20240501.120000.csv
trade-ETH-USD-20240501.120000.csv
```

## CSV 欄位假設

### `init`

每列代表初始 order book level：

| 欄位位置 | 意義 |
| - | - |
| `0` | `price` |
| `1` | `volume` |
| `2` | `side` |

### `updates`

每列代表單筆 level2 更新：

| 欄位位置 | 意義 |
| - | - |
| `0` | `event_time` |
| `1` | `price` |
| `2` | `volume` |
| `3` | `side` |

### `trades`

每列代表單筆成交：

| 欄位位置 | 意義 |
| - | - |
| `0` | `event_time` |
| `1` | `price` |
| `2` | `volume` |
| `3` | `side` |

`io.load_raw_dataset()` 目前透過 `_simulation_core.read_csv()` 以 `csv.QUOTE_NONNUMERIC` 讀入，因此所有值會轉成數值。

## 輸出檔名格式

`build_output_path()` 目前固定輸出：

```text
<product_id>-<timestamp>-<time_step>-resolved-<resolved_time>-simulation-<algorithm_name>.npz
```

例如：

```text
ETH-USD-20240501.120000-0.01-resolved-1.0-simulation-event_balanced.npz
```

這個檔名格式同時被以下模組依賴：

- `src/preprocess/catalog.py`
- `src/plots/discovery.py`

因此改檔名時必須同步修改解析 regex。

## `.npz` metadata keys

每個 simulation 輸出都會保存這些 metadata：

- `algorithm`
- `product_id`
- `file_stem`
- `time_step`
- `base_tick`
- `resolved_time`

## `.npz` result keys

### bid 側

- `bid_prices`
- `bid_near_size`
- `bid_opp_size`
- `bid_survival_time`
- `bid_ahead`
- `bid_behind`
- `bid_vorder_ratio`
- `bid_result`
- `bid_spread`
- `bid_mid_price`
- `bid_micro_price`
- `bid_mid_profit`
- `bid_micro_profit`

### ask 側

- `ask_prices`
- `ask_near_size`
- `ask_opp_size`
- `ask_survival_time`
- `ask_ahead`
- `ask_behind`
- `ask_vorder_ratio`
- `ask_result`
- `ask_spread`
- `ask_mid_price`
- `ask_micro_price`
- `ask_mid_profit`
- `ask_micro_profit`

## 關鍵欄位語意

### `near_size`

提交虛擬單當下，同側 best level 的 size。

### `opp_size`

提交虛擬單當下，對手側 best level 的 size。

### `ahead`

估計在虛擬單前方的 queue size。

### `behind`

估計在虛擬單後方的 queue size。

### `vorder_ratio`

`base_tick / best_size`，是目前虛擬單 size 與當下 best size 的比率。

### `survival_time`

該虛擬單從 submit 到 resolve 的時間差。若尚未 resolve，可能維持預設值或在下游被視為未決樣本。

### `result`

目前程式內的判定值：

- `1`: 成交
- `0`: 最終未成交，但已 resolve
- `-1`: 尚未 resolve

### `mid_price` / `micro_price`

在 `resolved_time` 視角下，根據 quote timeline 向前看得到的 mid / micro price。

計算時點：

- 若 `result == 1`，使用 `fill_time + resolved_time`
- 若 `result == 0`，使用 `submit_time + resolved_time`
- 若 `result == -1`，回傳 `NaN`

### `mid_profit` / `micro_profit`

以掛單價格為基準計算的 forward-looking profit。

- bid 側使用 `future_price - order.price`
- ask 側使用 `-(future_price - order.price)`

這樣 bid / ask 都能統一為「越大越有利」的方向。

## 下游讀取習慣

目前下游 plot 模組有兩個常見過濾規則：

- fill probability 類圖通常只使用 `result != -1`
- profit 類圖通常只使用 `result == 1`

因此若你新增欄位或改變 `result` 語意，應先檢查：

- `src/plots/fill_probability.py`
- `src/plots/profit_heatmap.py`
- `src/plots/cost_fill_probability.py`

## 空結果行為

若某批資料：

- 沒有 trades
- 或 simulation time window 為空

演算法會回傳固定 schema 的空 `numpy.ndarray`，而不是拋錯。這使得 batch pipeline 可以繼續跑，但下游可能需要自行處理空樣本情況。

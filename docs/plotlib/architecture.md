# `src.plotlib` Architecture

## Position in the pipeline

`src.plotlib` 位於 artifact consumption 端：

1. `src.preprocess` 產生 preprocessed artifact
2. `src.simulation` 產生 simulation artifact
3. `src.dataset_artifacts` 負責定位 artifact
4. `src.plotlib.loaders` 讀取 artifact
5. `src.plotlib.renderers` 建圖

## Internal layers

- `loaders/`
  - `.npz` / arrays -> normalized payload
- `types.py`
  - payload schema
- `options.py`
  - render options
- `views.py`
  - public facade
- `renderers/`
  - plotting implementations

## Boundary

`src.plotlib` 不應再維護：

- `time_step` normalization
- simulation filename regex
- simulation artifact lookup

這些規則的唯一實作在 `src.dataset_artifacts`。

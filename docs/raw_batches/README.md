# `src.raw_batches`

`src.raw_batches` 是原始 `data/v3` CSV 批次的唯一規則來源。

## Responsibilities

- raw CSV 檔名 parsing
- raw batch discovery
- `RawBatch` identity model
- raw batch loading
- timestamp parsing / unix conversion

## Main APIs

- `parse_raw_filename(filename)`
- `discover_raw_batches(raw_dir)`
- `load_raw_batch(batch)`
- `parse_timestamp(timestamp)`
- `file_time_to_unix(timestamp)`

# Operational Constraints

Do not perform bulk deletion of files or directories.

Do not use:

- `del /s`
- `rd /s`
- `rmdir /s`
- `Remove-Item -Recurse`
- `rm -rf`

When deleting a file, you may delete only one explicit file path at a time.

Correct example:

```powershell
Remove-Item "C:\path\to\file.txt"
```

If bulk deletion is required, stop and ask the user to delete the files manually.

The following directory name is exempt from the rule above and may be deleted directly. The task must still confirm whether it was actually deleted:

- `__pycache__/`

---

# project-doc

## Project Summary

This repository is a quantitative finance research project built around Coinbase market data. The current documentation focus is raw batch ingestion and windowed preprocess artifact generation.

1. `server/websocket.py`
   Runs a long-lived websocket subscription for `heartbeats`, `level2`, and `market_trades`, and writes raw CSV batches.
2. `src/raw_batches/`
   Handles raw CSV filename parsing, batch discovery, and loading.
3. `src/preprocess/`
   Converts `data/raw` batches into windowed preprocess `.npz` files.
4. `src/dataset_artifacts/`
   Scans `data/preprocessed` and builds the preprocess artifact catalog.
5. `result/convert_data.py`
   Runs batch conversion from `data/raw` to `data/preprocessed` for multiple trade windows.

The current mainline data flow is:

```text
data/raw CSV
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/preprocess-*.npz
  -> src.dataset_artifacts
```

## Directory Structure

- `server/`
  - `websocket.py`: Main data collection script. Validates `sequence_num` and heartbeat continuity and recreates the subscription when needed.
  - `config.json`: Collector settings, including `saving_interval` and a single `product_id`.
- `src/raw_batches/`
  - `api.py`: Raw CSV filename parsing, batch discovery, and CSV loading.
  - `__init__.py`: Public exports for the raw batch API.
- `src/preprocess/`
  - `pipeline.py`: Preprocess orchestration, `PLOT_REGISTRY`, and `.npz` writing.
  - `orderbook.py`: Windowed orderbook payload builder.
  - `trade.py`: Windowed trade aggregate payload builder.
  - `time_utils.py`: Shared event-time normalization and bucket-grid helpers.
  - `exceptions.py`: Preprocess-related exception types.
- `src/dataset_artifacts/`
  - `catalog.py`: Naming rules, parsing, catalog discovery, and view detection for preprocess artifacts.
  - `__init__.py`: Public exports for the artifact API.
- `result/`
  - `convert_data.py`: Converts complete raw batches from `data/raw` into preprocess artifacts in `data/preprocessed`.
- `data/`
  - `raw/`: Current mainline raw CSV batch format.
  - `preprocessed/`: Preprocess artifacts.
- `docs/`
  - Module documentation, contracts, and API notes for the current architecture.
- `test/`
  - Automated tests.
- `Assignment/`
  - Coursework or scratch material, not part of the mainline pipeline.
- `fig/`
  - Legacy plotting outputs and parameters, not part of the mainline pipeline.

## Execution And Behavior

- Python environment:
  - Always use the `quantitative_finance` environment for any Python command in this repository, including scripts, tests, and tooling.
  - Prefer `conda activate quantitative_finance` before running project commands in an interactive shell.
  - For one-off commands, prefer `conda run -n quantitative_finance ...` to avoid ambiguity about the active interpreter.
  - Do not use another Python environment unless the user explicitly asks for it.
- Raw data collection:
  - Use the `quantitative_finance` environment.
  - `server/websocket.py` should be run with `server/` as the working directory.
  - The script writes `level2-...csv` and `trade-...csv` to the current working directory. It does not automatically write into `data/`.
- Preprocessing:
  - Use the `quantitative_finance` environment.
  - `src.preprocess.preprocess_batch()` converts a single raw batch into preprocess artifacts in `data/preprocessed`.
  - `src.preprocess.preprocess_batches()` supports batch processing.
  - `result/convert_data.py` converts complete batches in `data/raw` for `trade_window_seconds` values `(1, 5, 10, 30)`.

## Data Formats

- `raw`
  - Current mainline single-product CSV batch format:
    - `level2-{product_id}-init-{timestamp}.csv`
    - `level2-{product_id}-updates-{timestamp}.csv`
    - `trade-{product_id}-{timestamp}.csv`
- `preprocessed orderbook dataset`
  - Filename format:
    - `preprocess-orderbook-{preprocess_timestamp}.npz`
- `preprocessed trade dataset`
  - Filename format:
    - `preprocess-trade-{preprocess_timestamp}.npz`

## Dependency Status

`requirements.txt` currently lists:

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

## Important Notes

- `server/websocket.py` currently supports only one product at a time.
- Timestamps in filenames use UTC.
- `data/` currently contains only `raw/` and `preprocessed/`.
- `data/preprocessed/` stores preprocess artifacts named `preprocess-{preprocess_type}-{preprocess_timestamp}.npz`.
- `src.preprocess.pipeline.PLOT_REGISTRY` determines which base preprocess payloads are produced.
- `src.dataset_artifacts.catalog` relies on filename regexes and `.npz` keys to build the catalog. If naming rules or payload keys change, update the related modules and docs together.
- The active `data/` layout is limited to `raw/` and `preprocessed/`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

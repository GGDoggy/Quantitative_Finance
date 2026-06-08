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

This repository is a quantitative finance research project built around Coinbase market data. The current mainline architecture is organized as follows:

1. `server/websocket.py`
   Runs a long-lived websocket subscription for `heartbeats`, `level2`, and `market_trades`, and writes raw CSV batches in the `data/v3` style.
2. `src/raw_batches/`
   Handles raw CSV filename parsing, batch discovery, and loading.
3. `src/preprocess/`
   Converts `data/v3` raw batches into preprocessed `.npz` files that the dashboard can consume.
4. `src/simulation/`
   Runs virtual order simulations on raw batches and writes simulation `.npz` artifacts.
5. `src/dataset_artifacts/`
   Scans `data/preprocessed` and builds the preprocessed and simulation artifact catalog.
6. `src/plotlib/`
   Converts preprocessed payloads or simulation arrays into HoloViews and Plotly visualizations.
7. `gui/webUI.py`
   Starts the Panel dashboard and integrates catalog discovery, preprocessing, simulation, and interactive visualization.

The current mainline data flow is:

```text
data/v3 CSV
  -> src.raw_batches
  -> src.preprocess
  -> data/preprocessed/*-orderbook_for_plot.npz
  -> src.plotlib
  -> gui/webUI.py

data/v3 CSV
  -> src.raw_batches
  -> src.simulation
  -> data/preprocessed/*-simulation-*.npz
  -> src.dataset_artifacts
  -> src.plotlib
  -> gui/webUI.py
```

## Directory Structure

- `server/`
  - `websocket.py`: Main data collection script. Validates `sequence_num` and heartbeat continuity and recreates the subscription when needed.
  - `config.json`: Collector settings, including `saving_interval` and a single `product_id`.
- `gui/`
  - `webUI.py`: Dashboard startup entrypoint that serves the Panel app.
  - `dashboard.py`: Main UI implementation, including product selection, catalog refresh, preprocessing, simulation, plot rendering, and settings persistence.
  - `styles.py`: Dashboard styling and UI constants.
  - `dashboard_settings.json`: Persisted simulation heatmap settings.
- `src/raw_batches/`
  - `api.py`: Raw CSV filename parsing, batch discovery, and CSV loading.
  - `__init__.py`: Public exports for the raw batch API.
- `src/preprocess/`
  - `catalog.py`: Dashboard-facing catalog helpers, payload loading, and simulation artifact matching.
  - `pipeline.py`: Preprocess orchestration, `PLOT_REGISTRY`, and `.npz` writing.
  - `orderbook.py`: Orderbook payload builder.
  - `exceptions.py`: Preprocess-related exception types.
- `src/dataset_artifacts/`
  - `catalog.py`: Naming rules, parsing, catalog discovery, and view detection for preprocessed and simulation artifacts.
  - `__init__.py`: Public exports for the artifact API.
- `src/plotlib/`
  - `registry.py`: Dashboard plot registry defining plot types, labels, loaders, builders, and simulation requirements.
  - `orderbook.py`: HoloViews orderbook payload loading and view building.
  - `trades.py`: Plotly trades scatter and trade volume timeline loading and view building.
  - `simulation_heatmaps.py`: Fill probability, profit, and cost-filtered heatmap builders.
  - `options.py`, `types.py`, `errors.py`: Payload normalization, render options, and plot-related exceptions.
- `src/simulation/`
  - `service.py`: Raw dataset loading, simulation orchestration, parallel execution, and `.npz` writing.
  - `algorithms.py`: Registered algorithms and the three current simulation entrypoints.
  - `core.py`: Shared simulation logic.
  - `models.py`: Request and result models.
- `data/`
  - `v1/`: Legacy snapshot-only JSON format.
  - `v2/`: Legacy level2 and trade JSON format.
  - `v3/`: Current mainline raw CSV batch format.
  - `preprocessed/`: Base datasets and simulation artifacts.
- `docs/`
  - Module documentation, contracts, and API notes for the current architecture.
- `test/`
  - Library-level tests, refactor tests, and dashboard smoke tests.
- `Assignment/`
  - Coursework or analysis scratch material, not part of the mainline pipeline.
- `fig/`
  - Legacy plotting outputs and parameters, not part of the mainline pipeline.

## Execution And Behavior

- Raw data collection:
  - `server/websocket.py` should be run with `server/` as the working directory.
  - The script writes `level2-...csv` and `trade-...csv` to the current working directory. It does not automatically write into `data/`.
- Dashboard startup:
  - Run `python gui/webUI.py` from the repository root.
  - The default raw data directory is `data/v3`.
  - The default preprocessed directory is `data/preprocessed`.
  - `gui/webUI.py` serves the app with `pn.serve(build_app, title="Orderbook Viewer", show=True)`.
- Preprocessing:
  - `src.preprocess.preprocess_batch()` converts a single raw batch into `*-orderbook_for_plot.npz`.
  - `src.preprocess.preprocess_batches()` supports batch processing.
  - `gui/dashboard.py` exposes raw batch catalog discovery and preprocess actions in the UI.
- Simulation:
  - `src.simulation.simulate_batch()` and `simulate_batches()` write outputs to `data/preprocessed/`.
  - Simulation filenames include `time_step`, `resolved_time`, and `algorithm_name`.
  - `gui/dashboard.py` can run simulation directly from the UI on selected raw batches.
- Visualization:
  - Current base plots include `Orderbook`, `Trades Scatter`, and `Trade Volume Timeline`.
  - Current simulation plots include `Fill Probability`, `Mid Profit`, `Micro Profit`, and two cost-filtered fill probability heatmaps.
  - Plot availability is driven by `src.plotlib.registry.APP_PLOT_REGISTRY`.

## Data Formats

- `v1`
  - Legacy snapshot-only JSON.
- `v2`
  - Legacy multi-product JSON event format.
- `v3`
  - Current mainline single-product CSV batch format:
    - `level2-{product_id}-init-{timestamp}.csv`
    - `level2-{product_id}-updates-{timestamp}.csv`
    - `trade-{product_id}-{timestamp}.csv`
- `preprocessed orderbook dataset`
  - Filename format:
    - `{product_id}-{timestamp}-{time_step}-orderbook_for_plot.npz`
- `simulation dataset`
  - Filename format:
    - `{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}-simulation-{algorithm_name}.npz`

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
- `data/preprocessed/` currently mixes two output categories:
  - `*-orderbook_for_plot.npz`
  - `*-simulation-*.npz`
- `src.preprocess.pipeline.PLOT_REGISTRY` determines which base preprocess payloads are produced.
- `src.dataset_artifacts.catalog` relies on filename regexes and `.npz` keys to build the catalog. If naming rules or payload keys change, update the related modules and docs together.
- `src.plotlib.registry.APP_PLOT_REGISTRY` is the central registration point for dashboard plot availability.
- `Assignment/`, `fig/v1/`, `data/v1/`, and `data/v2/` are legacy or experimental artifacts and should not be treated as the current production pipeline.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

# `src.plots` deprecation and migration plan

## Stage A — introduction phase

- `src/plots/*` is treated as a **shim-only** package.
- Shim modules may only re-export public API intended to live in `src.plotlib`.
- Do **not** add file I/O, catalog lookup, or registry decision logic to shim modules.

## Stage B — convergence phase

1. Build migration inventory from repo usage:
   - `rg "from src\.plots|import src\.plots" -n`
2. Migrate each callsite to:
   - `src.plotlib` (preferred), or
   - app-level registry module (for example `gui/plot_registry.py`).
3. Keep the inventory shrinking by updating `tools/src_plots_import_allowlist.txt` only when a path is removed.

## Stage C — removal phase

- Once `rg "src\.plots"` only matches shim internals and deprecation tests, remove `src/plots` shim package.
- In changelog/PR description, record:
  - removal date,
  - replacement import path mapping.

## CI / pre-commit guard

Use this check in CI or pre-commit to prevent new `src.plots` dependencies:

```bash
python scripts/check_src_plots_imports.py
```

The check fails when a new non-allowlisted file adds `from src.plots ...` or `import src.plots ...`.

## 2026-05-22 Stage B implementation log

- Stage B status: completed for repo production callers.
- Removed direct `src.plots` imports from:
  - `gui/rendering.py`
  - `gui/simulation_controls.py`
  - `src/app_plot_registry.py`
  - `src/preprocess/service.py`
- Promoted `src.plotlib` to the stable entrypoint for:
  - render options and dashboard simulation heatmap settings
  - plot locator / builder protocols
  - app-layer plot builders via thin compatibility adapters
- Added a dedicated preprocess registry in `src.preprocess.registry` so preprocess no longer depends on the legacy plot registry.
- Reduced `tools/src_plots_import_allowlist.txt` to comments only because no production caller still requires an exception.
- Stage B acceptance result:
  - `python scripts/check_import_boundaries.py` passes
  - `python scripts/check_src_plots_imports.py` passes
  - `test/test_import_boundaries.py` passes
- Remaining Stage C work:
  - move renderer implementations out of `src/plots/*` into `src/plotlib/*`
  - remove shim-only modules after legacy imports disappear outside shim internals and deprecation coverage
  - record final removal date and replacement path mapping when `src/plots` is deleted

# `src.plots` migration status

## Status

- Stage C completed on 2026-05-22.
- `src.plots` has been removed from the repo.
- `src.plotlib` is now the only plotting library entrypoint.

## Final replacement paths

- Render options and public plot builders: `src.plotlib`
- App registry metadata: `src.app_plot_registry`
- Dataset-to-payload conversion for GUI: `src.app_plot_adapters`
- Raw/preprocessed/simulation discovery: `src.preprocess.catalog`

## Checks

- `python scripts/check_import_boundaries.py`
- `python scripts/check_src_plots_imports.py`
- `python -m pytest test\test_import_boundaries.py`

## Notes

- Any new plotting code must live under `src.plotlib`.
- `src.plotlib` remains forbidden from importing `gui` or `src.preprocess`.

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

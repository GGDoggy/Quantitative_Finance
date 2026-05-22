"""Deprecated shim for legacy ``src.plots`` imports.

This package is in migration and should not receive new business logic.

Stage A (introduction)
----------------------
- ``src.plots`` may only re-export public API from ``src.plotlib``.
- No new file I/O, catalog queries, or registry decision logic is allowed in shim modules.

Stage B (convergence)
---------------------
- Build a repo-wide migration list via ``rg "src\\.plots"``.
- Migrate each import to ``src.plotlib`` or app-level registry modules
  (for example ``gui/plot_registry.py`` once available).

Stage C (removal)
-----------------
- Remove this shim after ``rg "src\\.plots"`` only matches shim internals
  and deprecation tests.
- In the removal changelog, record removal date and replacement import paths.
"""

from __future__ import annotations

import warnings


def warn_deprecated_import() -> None:
    """Emit deprecation warning for callers that opt in to migration nudges."""
    warnings.warn(
        "src.plots is deprecated and will be removed after migration to src.plotlib. "
        "Please migrate imports.",
        DeprecationWarning,
        stacklevel=2,
    )

from .errors import PreprocessedDataError
from .registry import PLOT_LABELS, PLOT_REGISTRY, PlotSpec
from .settings import DashboardSimulationHeatmapSettings, PlotRenderOptions

__all__ = [
    "DashboardSimulationHeatmapSettings",
    "PLOT_LABELS",
    "PLOT_REGISTRY",
    "PlotRenderOptions",
    "PlotSpec",
    "PreprocessedDataError",
    "warn_deprecated_import",
]

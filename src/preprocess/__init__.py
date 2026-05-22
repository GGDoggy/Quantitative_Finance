"""Public API for preprocess discovery, loading, and batch preprocessing.

Stable API surface:
- Exceptions under ``src.preprocess.exceptions`` re-exported here.
- Catalog models/discovery helpers used by dashboard and simulation flows.
- Batch preprocess entry points in ``src.preprocess.service``.

Internal APIs remain importable through explicit submodules. A small set of
legacy symbols stays temporarily available from this package root and emits a
DeprecationWarning.
"""
from __future__ import annotations

from warnings import warn

from .exceptions import (
    PreprocessError,
    PreprocessOutputConflictError,
    PreprocessValidationError,
    PreprocessedDataError,
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
)
from .catalog import (
    PlotDatasetLocator,
    PreprocessedDataset,
    RawBatch,
    discover_preprocessed_datasets,
    discover_raw_batches,
    load_preprocessed_payload,
)
from .service import DEFAULT_TIME_STEP, preprocess_batch, preprocess_batches


__all__ = [
    "PreprocessError",
    "PreprocessOutputConflictError",
    "PreprocessValidationError",
    "PreprocessedDataError",
    "PreprocessedDataFileError",
    "PreprocessedDataSchemaError",
    "PlotDatasetLocator",
    "PreprocessedDataset",
    "RawBatch",
    "discover_preprocessed_datasets",
    "discover_raw_batches",
    "load_preprocessed_payload",
    "DEFAULT_TIME_STEP",
    "preprocess_batch",
    "preprocess_batches",
]

_DEPRECATED_ALIASES = {
    "detect_available_views": (
        "src.preprocess.catalog.detect_available_views",
        "Import detect_available_views from src.preprocess.catalog instead.",
    ),
    "find_simulation_files": (
        "src.preprocess.catalog.find_simulation_files",
        "Import find_simulation_files from src.preprocess.catalog instead.",
    ),
    "format_time_step": (
        "src.preprocess.catalog.format_time_step",
        "Import format_time_step from src.preprocess.catalog instead.",
    ),
    "has_simulation_file": (
        "src.preprocess.catalog.has_simulation_file",
        "Import has_simulation_file from src.preprocess.catalog instead.",
    ),
    "parse_timestamp": (
        "src.preprocess.catalog.parse_timestamp",
        "Import parse_timestamp from src.preprocess.catalog instead.",
    ),
    "PreprocessContext": (
        "src.preprocess.common.PreprocessContext",
        "Import PreprocessContext from src.preprocess.common instead.",
    ),
    "build_context": (
        "src.preprocess.common.build_context",
        "Import build_context from src.preprocess.common instead.",
    ),
}


def __getattr__(name: str):
    deprecated = _DEPRECATED_ALIASES.get(name)
    if deprecated is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    target, hint = deprecated
    module_name, attribute_name = target.rsplit(".", maxsplit=1)
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    warn(
        (
            f"src.preprocess.{name} is deprecated and will be removed from package-level "
            f"exports in a future release. {hint}"
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return value

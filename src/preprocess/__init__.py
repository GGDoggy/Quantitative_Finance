"""Public API for preprocess discovery, models, and batch preprocessing."""
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
    discover_preprocessed_datasets,
    discover_raw_batches,
    find_simulation_files,
    format_time_step,
    has_simulation_file,
    load_preprocessed_payload,
    parse_timestamp,
)
from .models import PlotDatasetLocator, PreprocessContext, PreprocessedDataset, RawBatch
from .service import DEFAULT_TIME_STEP, preprocess_batch, preprocess_batches


__all__ = [
    "RawBatch",
    "PreprocessedDataset",
    "PlotDatasetLocator",
    "PreprocessContext",
    "discover_raw_batches",
    "discover_preprocessed_datasets",
    "find_simulation_files",
    "has_simulation_file",
    "format_time_step",
    "parse_timestamp",
    "load_preprocessed_payload",
    "DEFAULT_TIME_STEP",
    "preprocess_batch",
    "preprocess_batches",
    "PreprocessError",
    "PreprocessOutputConflictError",
    "PreprocessValidationError",
    "PreprocessedDataError",
    "PreprocessedDataFileError",
    "PreprocessedDataSchemaError",
]

_DEPRECATED_ALIASES = {
    "detect_available_views": (
        "src.preprocess.catalog.detect_available_views",
        "Import detect_available_views from src.preprocess.catalog instead.",
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

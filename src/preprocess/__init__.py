"""Public API for preprocess orchestration and payload validation."""
from .exceptions import (
    PreprocessError,
    PreprocessOutputConflictError,
    PreprocessValidationError,
    PreprocessedDataError,
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
)
from .datasets import (
    discover_preprocessed_datasets,
    discover_raw_batches,
    find_simulation_files,
    format_time_step,
    has_simulation_file,
    load_preprocessed_payload,
    parse_timestamp,
)
from .models import PlotDatasetLocator, PreprocessContext, PreprocessedDataset, RawBatch
from .registry import PLOT_REGISTRY, PreprocessBuilderSpec
from .service import DEFAULT_TIME_STEP, preprocess_batch, preprocess_batches


__all__ = [
    "RawBatch",
    "PreprocessedDataset",
    "PlotDatasetLocator",
    "PreprocessContext",
    "PreprocessBuilderSpec",
    "PLOT_REGISTRY",
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

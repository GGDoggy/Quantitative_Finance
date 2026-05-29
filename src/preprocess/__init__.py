"""Public API for preprocess orchestration and payload validation."""
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
    detect_available_views,
    find_simulation_files,
    format_resolved_time,
    format_time_step,
    has_simulation_file,
    load_preprocessed_payload,
    parse_timestamp,
)
from .pipeline import (
    DEFAULT_TIME_STEP,
    PLOT_REGISTRY,
    PreprocessBuilderSpec,
    PreprocessContext,
    preprocess_batch,
    preprocess_batches,
)
from src.dataset_artifacts import DatasetLocator as PlotDatasetLocator
from src.dataset_artifacts import PreprocessedArtifact as PreprocessedDataset
from src.raw_batches import RawBatch


__all__ = [
    "RawBatch",
    "PreprocessedDataset",
    "PlotDatasetLocator",
    "PreprocessContext",
    "PreprocessBuilderSpec",
    "PLOT_REGISTRY",
    "discover_raw_batches",
    "discover_preprocessed_datasets",
    "detect_available_views",
    "find_simulation_files",
    "has_simulation_file",
    "format_resolved_time",
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

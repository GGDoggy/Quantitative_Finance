"""Public API for preprocess orchestration and payload validation."""
from .exceptions import (
    PreprocessError,
    PreprocessValidationError,
)
from .pipeline import (
    DEFAULT_DEPTH,
    PLOT_REGISTRY,
    PreprocessBuilderSpec,
    PreprocessContext,
    preprocess_batch,
    preprocess_batches,
)


__all__ = [
    "PreprocessContext",
    "PreprocessBuilderSpec",
    "PLOT_REGISTRY",
    "DEFAULT_DEPTH",
    "preprocess_batch",
    "preprocess_batches",
    "PreprocessError",
    "PreprocessValidationError",
]

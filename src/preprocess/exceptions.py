"""Custom exceptions for preprocess discovery and payload loading."""
from __future__ import annotations


class PreprocessError(RuntimeError):
    """Base error for preprocess pipeline failures."""


class PreprocessValidationError(PreprocessError, ValueError):
    """Raised when preprocess input parameters are invalid."""


class PreprocessOutputConflictError(PreprocessError, ValueError):
    """Raised when multiple builders emit conflicting payload values."""


class PreprocessedDataError(PreprocessError):
    """Base error for preprocessed dataset IO/schema failures."""


class PreprocessedDataFileError(PreprocessedDataError):
    """Raised when a preprocessed dataset cannot be read as a valid NPZ file."""


class PreprocessedDataSchemaError(PreprocessedDataError):
    """Raised when a preprocessed dataset content is missing required schema."""

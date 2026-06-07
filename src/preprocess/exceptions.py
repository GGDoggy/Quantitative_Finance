"""Custom exceptions for preprocess pipeline failures."""
from __future__ import annotations


class PreprocessError(RuntimeError):
    """Base error for preprocess pipeline failures."""


class PreprocessValidationError(PreprocessError, ValueError):
    """Raised when preprocess input parameters are invalid."""

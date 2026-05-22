from __future__ import annotations


class PayloadSchemaVersionError(ValueError):
    """Raised when a payload schema version does not match renderer expectations."""

    def __init__(self, payload_name: str, expected: str, actual: str | None) -> None:
        actual_label = actual if actual is not None else "<missing>"
        super().__init__(
            f"{payload_name} schema_version mismatch: expected '{expected}', got '{actual_label}'."
        )
        self.payload_name = payload_name
        self.expected = expected
        self.actual = actual


class PreprocessedDataError(RuntimeError):
    """Raised when preprocessed dataset inspection/loading fails."""


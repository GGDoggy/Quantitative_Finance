from __future__ import annotations

import importlib


def test_preprocess_public_api_surface_is_explicit_and_stable():
    module = importlib.import_module("src.preprocess")

    expected_exports = {
        "DEFAULT_TIME_STEP",
        "PlotDatasetLocator",
        "PreprocessError",
        "PreprocessContext",
        "PreprocessOutputConflictError",
        "PreprocessValidationError",
        "PreprocessedDataError",
        "PreprocessedDataFileError",
        "PreprocessedDataSchemaError",
        "PreprocessedDataset",
        "RawBatch",
        "discover_preprocessed_datasets",
        "discover_raw_batches",
        "find_simulation_files",
        "format_time_step",
        "has_simulation_file",
        "load_preprocessed_payload",
        "parse_timestamp",
        "preprocess_batch",
        "preprocess_batches",
    }

    assert set(module.__all__) == expected_exports
    for name in module.__all__:
        assert hasattr(module, name), f"Missing importable public API: {name}"

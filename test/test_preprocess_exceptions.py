from __future__ import annotations

import numpy as np

from src.preprocess import (
    PreprocessedDataset,
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
    discover_preprocessed_datasets,
    load_preprocessed_payload,
)


def _discover_one_dataset(tmp_path):
    datasets = discover_preprocessed_datasets(tmp_path)
    assert len(datasets) == 1
    return datasets[0]


def test_load_preprocessed_payload_raises_file_error_for_invalid_npz(tmp_path):
    path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    path.write_bytes(b"not a zip archive")

    dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        path=path,
        available_views=("orderbook",),
    )
    try:
        load_preprocessed_payload(dataset)
    except PreprocessedDataFileError as exc:
        assert "Failed to load" in str(exc)
        assert path.name in str(exc)
    else:
        raise AssertionError("Expected PreprocessedDataFileError")


def test_load_preprocessed_payload_raises_schema_error_for_missing_fields(tmp_path):
    path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    np.savez(path, price_axis=np.array([1.0]), time_axis=np.array([1.0]))

    dataset = _discover_one_dataset(tmp_path)
    try:
        load_preprocessed_payload(dataset)
    except PreprocessedDataSchemaError as exc:
        message = str(exc)
        assert "missing required fields" in message
        assert "data" in message
    else:
        raise AssertionError("Expected PreprocessedDataSchemaError")


def test_load_preprocessed_payload_raises_schema_error_for_mismatched_shapes(tmp_path):
    path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    np.savez(
        path,
        price_axis=np.array([1.0]),
        time_axis=np.array([1.0, 2.0]),
        data=np.ones((2, 2)),
        bid=np.ones((2, 1)),
        ask=np.ones((2, 2)),
    )

    dataset = _discover_one_dataset(tmp_path)
    try:
        load_preprocessed_payload(dataset)
    except PreprocessedDataSchemaError as exc:
        assert "mismatched data/bid/ask shapes" in str(exc)
    else:
        raise AssertionError("Expected PreprocessedDataSchemaError")

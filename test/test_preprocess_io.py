from __future__ import annotations

import numpy as np
import pytest

from src.preprocess.exceptions import PreprocessedDataFileError, PreprocessedDataSchemaError
from src.preprocess.io import build_trade_arrays, detect_available_views, read_csv_rows
from src.preprocess.models import PreprocessedDataset


def test_read_csv_rows_reads_minimal_numeric_csv(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("1,2,3,4\n", encoding="utf-8")

    assert read_csv_rows(path) == [[1.0, 2.0, 3.0, 4.0]]


def test_read_csv_rows_returns_empty_for_empty_file(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("", encoding="utf-8")

    assert read_csv_rows(path) == []


def test_build_trade_arrays_handles_empty_rows():
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays([], "20240101.000000")

    assert trade_time.shape == (0,)
    assert trade_price.shape == (0,)
    assert trade_volume.shape == (0,)
    assert trade_side.shape == (0,)
    assert trade_price.dtype == float


def test_build_trade_arrays_handles_single_row():
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(
        [[1.5, 100.0, 2.0, -1.0]],
        "20240101.000000",
    )

    assert trade_time.shape == (1,)
    assert str(trade_time[0]) == "2024-01-01T00:00:01.500000000"
    assert trade_price.tolist() == [100.0]
    assert trade_volume.tolist() == [2.0]
    assert trade_side.tolist() == [-1.0]


def test_build_trade_arrays_handles_multiple_rows():
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(
        [[0.0, 100.0, 1.0, 1.0], [2.0, 101.0, 3.0, -1.0]],
        "20240101.000000",
    )

    assert trade_time.shape == (2,)
    assert trade_price.dtype == float
    assert trade_volume.dtype == float
    assert trade_side.dtype == float


def test_detect_available_views_prefers_available_views_field(tmp_path):
    path = tmp_path / "dataset.npz"
    np.savez(path, available_views=np.array(["z_view", "a_view"]), ignored=np.array([1.0]))

    assert detect_available_views(path, view_detector=lambda _keys: ("fallback",)) == ("z_view", "a_view")


def test_detect_available_views_uses_detector_when_available_views_missing(tmp_path):
    path = tmp_path / "dataset.npz"
    np.savez(path, price_axis=np.array([1.0]), data=np.array([1.0]))

    assert detect_available_views(path, view_detector=lambda keys: tuple(sorted(keys))) == (
        "data",
        "price_axis",
    )


def test_detect_available_views_raises_file_error_for_invalid_npz(tmp_path):
    path = tmp_path / "dataset.npz"
    path.write_bytes(b"invalid")

    with pytest.raises(PreprocessedDataFileError):
        detect_available_views(path)


def test_load_preprocessed_payload_reports_axis_dimensionality_errors(tmp_path):
    path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    np.savez(
        path,
        price_axis=np.array([[1.0]]),
        time_axis=np.array([1.0]),
        data=np.ones((1, 1)),
        bid=np.ones((1,)),
        ask=np.ones((1,)),
    )

    dataset = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        path=path,
        available_views=("orderbook",),
    )

    from src.preprocess.io import load_preprocessed_payload

    with pytest.raises(PreprocessedDataSchemaError) as exc:
        load_preprocessed_payload(dataset)

    assert "invalid axis dimensionality" in str(exc.value)

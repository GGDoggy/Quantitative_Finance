from __future__ import annotations

from pathlib import Path

import numpy as np

from gui.data_catalog import discover_preprocessed_datasets, discover_raw_batches


PRODUCT_ID = "ETH-USD"
TIMESTAMP = "20240101.000000"
TIME_STEP = "0.01"


def _touch_raw_batch(raw_dir: Path) -> None:
    (raw_dir / f"level2-{PRODUCT_ID}-init-{TIMESTAMP}.csv").write_text("")
    (raw_dir / f"level2-{PRODUCT_ID}-updates-{TIMESTAMP}.csv").write_text("")
    (raw_dir / f"trade-{PRODUCT_ID}-{TIMESTAMP}.csv").write_text("")


def _write_orderbook_npz(path: Path) -> None:
    np.savez(
        path,
        price_axis=np.array([1.0]),
        time_axis=np.array([0.0]),
        data=np.array([[1.0]]),
        bid=np.array([1.0]),
        ask=np.array([1.0]),
    )


def test_simulation_only_dataset_does_not_mark_raw_batch_preprocessed(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    preprocessed_dir = tmp_path / "preprocessed"
    raw_dir.mkdir()
    preprocessed_dir.mkdir()
    _touch_raw_batch(raw_dir)

    np.savez(preprocessed_dir / f"{PRODUCT_ID}-{TIMESTAMP}-{TIME_STEP}-simulation.npz")

    datasets = discover_preprocessed_datasets(preprocessed_dir)
    assert len(datasets) == 1
    assert datasets[0].available_views == ("fill_probability",)

    batches = discover_raw_batches(raw_dir, preprocessed_dir)
    assert len(batches) == 1
    assert not batches[0].is_preprocessed


def test_orderbook_dataset_marks_raw_batch_preprocessed(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    preprocessed_dir = tmp_path / "preprocessed"
    raw_dir.mkdir()
    preprocessed_dir.mkdir()
    _touch_raw_batch(raw_dir)
    _write_orderbook_npz(
        preprocessed_dir / f"{PRODUCT_ID}-{TIMESTAMP}-{TIME_STEP}-orderbook_for_plot.npz"
    )

    batches = discover_raw_batches(raw_dir, preprocessed_dir)
    assert len(batches) == 1
    assert batches[0].is_preprocessed

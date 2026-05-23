from __future__ import annotations

from pathlib import Path

import numpy as np

from src.preprocess import discover_preprocessed_datasets, discover_raw_batches, preprocess_batch
from src.preprocess.catalog import SIMULATION_VIEW_KEYS
from src.preprocess.models import PlotDatasetLocator, RawBatch


def _touch_csv(path: Path, rows: str = "1,2,3,4\n") -> None:
    path.write_text(rows, encoding="utf-8")


def _write_valid_orderbook_npz(
    path: Path,
    *,
    available_views: tuple[str, ...] | None = None,
) -> None:
    payload = {
        "price_axis": np.array([100.0, 101.0]),
        "time_axis": np.array(["2024-01-01T00:00:01", "2024-01-01T00:00:02"], dtype="datetime64[ns]"),
        "data": np.array([[1.0, -1.0], [2.0, -2.0]]),
        "bid": np.array([100.0, 100.5]),
        "ask": np.array([101.0, 101.5]),
    }
    if available_views is not None:
        payload["available_views"] = np.array(available_views)
    np.savez(path, **payload)


def _make_raw_triplet(root: Path, product_id: str, timestamp: str) -> RawBatch:
    init_path = root / f"level2-{product_id}-init-{timestamp}.csv"
    updates_path = root / f"level2-{product_id}-updates-{timestamp}.csv"
    trade_path = root / f"trade-{product_id}-{timestamp}.csv"
    _touch_csv(init_path, "100,1,1\n101,1,-1\n")
    _touch_csv(updates_path, "1,100,2,1\n2,101,0,-1\n")
    _touch_csv(trade_path, "1.5,100.5,0.25,-1\n")
    return RawBatch(
        product_id=product_id,
        timestamp=timestamp,
        init_path=init_path,
        updates_path=updates_path,
        trade_path=trade_path,
    )


def test_discover_raw_batches_skips_incomplete_triplets(tmp_path):
    product_id = "ETH-USD"
    timestamp = "20240101.000000"
    _touch_csv(tmp_path / f"level2-{product_id}-init-{timestamp}.csv")
    _touch_csv(tmp_path / f"trade-{product_id}-{timestamp}.csv")

    batches = discover_raw_batches(tmp_path, tmp_path / "preprocessed")

    assert batches == []


def test_discover_raw_batches_marks_preprocessed_batches(tmp_path):
    product_id = "ETH-USD"
    timestamp = "20240101.000000"
    _make_raw_triplet(tmp_path, product_id, timestamp)
    preprocessed_dir = tmp_path / "preprocessed"
    preprocessed_dir.mkdir()
    _write_valid_orderbook_npz(
        preprocessed_dir / f"{product_id}-{timestamp}-0.01-orderbook_for_plot.npz",
        available_views=("orderbook",),
    )

    batches = discover_raw_batches(tmp_path, preprocessed_dir)

    assert len(batches) == 1
    assert batches[0].product_id == product_id
    assert batches[0].timestamp == timestamp
    assert batches[0].is_preprocessed is True


def test_discover_preprocessed_datasets_with_orderbook_only(tmp_path):
    path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    _write_valid_orderbook_npz(path, available_views=("orderbook", "trades_scatter"))

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.path == path
    assert dataset.simulation_path is None
    assert dataset.available_views == ("orderbook", "trades_scatter")


def test_discover_preprocessed_datasets_with_simulation_only(tmp_path):
    simulation_path = (
        tmp_path / "ETH-USD-20240101.000000-0.01-resolved-1-simulation-event_balanced.npz"
    )
    simulation_path.write_bytes(b"")

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.path == simulation_path
    assert dataset.simulation_path == simulation_path
    assert dataset.available_views == SIMULATION_VIEW_KEYS


def test_discover_preprocessed_datasets_with_orderbook_and_simulation(tmp_path):
    orderbook_path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    simulation_path = (
        tmp_path / "ETH-USD-20240101.000000-0.01-resolved-1-simulation-event_balanced.npz"
    )
    _write_valid_orderbook_npz(orderbook_path, available_views=("orderbook",))
    simulation_path.write_bytes(b"")

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.path == orderbook_path
    assert dataset.simulation_path == simulation_path
    assert dataset.available_views == ("orderbook", *SIMULATION_VIEW_KEYS)
    assert isinstance(dataset.available_views, tuple)


def test_preprocess_batch_integration_round_trip(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "preprocessed"
    batch = _make_raw_triplet(raw_dir, "ETH-USD", "20240101.000000")

    dataset = preprocess_batch(batch, output_dir=output_dir, time_step=0.01)

    rediscovered = discover_preprocessed_datasets(output_dir)
    assert len(rediscovered) == 1
    rediscovered_dataset = rediscovered[0]

    assert dataset.path.name == "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    assert dataset.available_views == (
        "orderbook",
        "trades_scatter",
        "trade_volume_timeline",
    )
    with np.load(dataset.path, allow_pickle=False) as payload:
        assert set(payload.files) >= {
            "available_views",
            "price_axis",
            "time_axis",
            "data",
            "bid",
            "ask",
            "trade_time",
            "trade_price",
            "trade_volume",
            "trade_side",
        }
    assert rediscovered_dataset.display_name == dataset.display_name
    assert rediscovered_dataset.dataset_id == dataset.dataset_id

    locator = rediscovered_dataset.to_locator(output_dir)
    assert isinstance(locator, PlotDatasetLocator)
    assert locator.path == dataset.path

from __future__ import annotations

import csv
from pathlib import Path

from src.app_plot_registry import get_dataset_plot_types
from src.plotlib.loaders import load_orderbook_payload, load_trades_payload
from src.preprocess.catalog import RawBatch, discover_preprocessed_datasets
from src.preprocess.service import preprocess_batch


def _write_csv(path: Path, rows: list[list[float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rows)


def test_preprocess_batch_writes_loader_compatible_dataset(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "preprocessed"
    raw_dir.mkdir()
    out_dir.mkdir()

    init_path = raw_dir / "level2-ETH-USD-init-20240101.000000.csv"
    updates_path = raw_dir / "level2-ETH-USD-updates-20240101.000000.csv"
    trade_path = raw_dir / "trade-ETH-USD-20240101.000000.csv"

    _write_csv(init_path, [[100.0, 1.0, 1.0], [101.0, 1.0, -1.0]])
    _write_csv(updates_path, [[0.5, 100.0, 2.0, 1.0], [0.5, 101.0, 2.0, -1.0]])
    _write_csv(trade_path, [[0.5, 100.5, 1.5, 1.0], [0.7, 100.6, 2.0, -1.0]])

    batch = RawBatch(
        product_id="ETH-USD",
        timestamp="20240101.000000",
        init_path=init_path,
        updates_path=updates_path,
        trade_path=trade_path,
    )

    dataset = preprocess_batch(batch, out_dir, time_step=0.01)

    orderbook_payload = load_orderbook_payload(
        dataset.path,
        product_id=dataset.product_id,
        timestamp=dataset.timestamp,
        time_step=dataset.time_step,
    )
    trades_payload = load_trades_payload(
        dataset.path,
        product_id=dataset.product_id,
        timestamp=dataset.timestamp,
        time_step=dataset.time_step,
    )
    discovered = discover_preprocessed_datasets(out_dir)

    assert orderbook_payload["schema_version"] == "1"
    assert trades_payload["schema_version"] == "1"
    assert dataset.available_views == (
        "orderbook",
        "trades_scatter",
        "trade_volume_timeline",
    )
    assert get_dataset_plot_types(dataset) == dataset.available_views
    assert [item.path for item in discovered] == [dataset.path]

from __future__ import annotations

import numpy as np

from gui.dashboard import OrderbookDashboard


def _write_valid_orderbook_npz(path, *, available_views: tuple[str, ...] | None = None):
    payload = {
        "price_axis": np.array([100.0, 101.0]),
        "time_axis": np.array(
            ["2024-01-01T00:00:01", "2024-01-01T00:00:02"], dtype="datetime64[ns]"
        ),
        "data": np.array([[1.0, -1.0], [2.0, -2.0]]),
        "bid": np.array([100.0, 100.5]),
        "ask": np.array([101.0, 101.5]),
    }
    if available_views is not None:
        payload["available_views"] = np.array(available_views)
    np.savez(path, **payload)


def test_orderbook_dashboard_initializes_with_empty_catalog(tmp_path):
    raw_dir = tmp_path / "raw"
    preprocessed_dir = tmp_path / "preprocessed"
    raw_dir.mkdir()
    preprocessed_dir.mkdir()

    dashboard = OrderbookDashboard(
        raw_dir=raw_dir,
        preprocessed_dir=preprocessed_dir,
        settings_path=tmp_path / "dashboard_settings.json",
        project_root=tmp_path,
    )

    assert dashboard.preprocessed_datasets == []
    assert dashboard.raw_by_label == {}
    assert dashboard.all_raw_by_label == {}


def test_orderbook_dashboard_refresh_catalog_discovers_simulation_datasets(tmp_path):
    raw_dir = tmp_path / "raw"
    preprocessed_dir = tmp_path / "preprocessed"
    raw_dir.mkdir()
    preprocessed_dir.mkdir()

    orderbook_path = preprocessed_dir / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    simulation_path = (
        preprocessed_dir
        / "ETH-USD-20240101.000000-0.01-resolved-1-simulation-event_balanced.npz"
    )
    _write_valid_orderbook_npz(orderbook_path)
    simulation_path.write_bytes(b"")

    dashboard = OrderbookDashboard(
        raw_dir=raw_dir,
        preprocessed_dir=preprocessed_dir,
        settings_path=tmp_path / "dashboard_settings.json",
        project_root=tmp_path,
    )

    assert len(dashboard.preprocessed_datasets) == 1
    dataset = dashboard.preprocessed_datasets[0]
    assert dataset.path == orderbook_path
    assert dataset.simulation_path == simulation_path
    assert dataset.available_views == (
        "orderbook",
        "fill_probability",
        "mid_profit",
        "micro_profit",
        "mid_fill_probability_cost",
        "micro_fill_probability_cost",
    )

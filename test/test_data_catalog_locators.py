import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.data_catalog import (
    PlotDatasetLocator,
    discover_preprocessed_datasets,
    load_preprocessed_payload,
)


def write_minimal_npz(path: Path) -> None:
    np.savez(
        path,
        price_axis=np.array([100.0]),
        time_axis=np.array(["2026-01-01T00:00:00.000000000"], dtype="datetime64[ns]"),
        data=np.array([[1.0]]),
        bid=np.array([99.0]),
        ask=np.array([101.0]),
        trade_time=np.array(["2026-01-01T00:00:00.000000000"], dtype="datetime64[ns]"),
        trade_price=np.array([100.0]),
        trade_volume=np.array([0.5]),
        trade_side=np.array([-1.0]),
    )


def test_locator_preserves_discovered_noncanonical_npz_path(tmp_path):
    npz_path = tmp_path / "ETH-USD-20260101.000000-1e-05-orderbook_for_plot.npz"
    write_minimal_npz(npz_path)

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    locator = datasets[0].to_locator(tmp_path)
    assert locator.path == npz_path
    assert locator.base_id == "ETH-USD-20260101.000000-1e-05"


def test_locator_payload_cache_reuses_loaded_npz(monkeypatch, tmp_path):
    npz_path = tmp_path / "ETH-USD-20260101.000000-0.0100-orderbook_for_plot.npz"
    write_minimal_npz(npz_path)
    real_load = np.load
    load_count = 0

    def counting_load(*args, **kwargs):
        nonlocal load_count
        load_count += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr("gui.data_catalog.np.load", counting_load)
    payload_cache = {}
    locator = PlotDatasetLocator(
        product_id="ETH-USD",
        timestamp="20260101.000000",
        time_step=0.01,
        preprocessed_dir=tmp_path,
        time_step_token="0.0100",
        original_path=npz_path,
        payload_cache=payload_cache,
    )

    first_payload = load_preprocessed_payload(locator)
    second_payload = load_preprocessed_payload(locator)

    assert first_payload is second_payload
    assert load_count == 1
    assert list(payload_cache) == [npz_path]

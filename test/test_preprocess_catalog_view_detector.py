from __future__ import annotations

import numpy as np

from src.plots.registry import PLOT_REGISTRY
from src.preprocess.adapters.plot_registry_detector import PlotRegistryViewDetector
from src.preprocess.catalog import discover_preprocessed_datasets


def _write_preprocessed_npz(path, payload_keys):
    payload = {key: np.array([1.0]) for key in payload_keys}
    np.savez(path, **payload)


def test_discover_preprocessed_datasets_default_detector_uses_builtin_views(tmp_path):
    file_path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    _write_preprocessed_npz(file_path, ("price_axis", "time_axis", "data", "bid", "ask"))

    datasets = discover_preprocessed_datasets(tmp_path)

    assert len(datasets) == 1
    assert datasets[0].available_views == ("orderbook",)
    assert isinstance(datasets[0].available_views, tuple)


def test_discover_preprocessed_datasets_uses_injected_detector(tmp_path):
    view_key, spec = next(iter(PLOT_REGISTRY.items()))
    file_path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    _write_preprocessed_npz(file_path, spec.required_payload_keys)

    datasets = discover_preprocessed_datasets(
        tmp_path,
        view_detector=PlotRegistryViewDetector(PLOT_REGISTRY),
    )

    assert len(datasets) == 1
    assert datasets[0].available_views == (view_key,)
    assert isinstance(datasets[0].available_views, tuple)

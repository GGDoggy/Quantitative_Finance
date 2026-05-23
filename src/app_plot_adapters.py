from __future__ import annotations

from src.app_plot_registry import APP_PLOT_REGISTRY
from src.plotlib.loaders import (
    load_orderbook_payloads,
    load_simulation_arrays_from_metadata,
    load_trades_payloads,
)
from src.preprocess import PreprocessedDataset


def _orderbook_loader_inputs(
    datasets: list[PreprocessedDataset],
) -> list[tuple[object, str, str, float]]:
    return [
        (dataset.path, dataset.product_id, dataset.timestamp, dataset.time_step)
        for dataset in datasets
    ]


def _simulation_loader_inputs(datasets: list[PreprocessedDataset]) -> list[object]:
    simulation_paths = [
        dataset.simulation_path
        for dataset in datasets
        if dataset.simulation_path is not None
    ]
    if not simulation_paths:
        raise ValueError("Selected datasets do not include simulation files.")
    return simulation_paths


def load_plot_input(plot_type: str, datasets: list[PreprocessedDataset]):
    payload_type = APP_PLOT_REGISTRY[plot_type].required_payload_type
    if payload_type == "orderbook":
        return load_orderbook_payloads(_orderbook_loader_inputs(datasets))
    if payload_type == "trades":
        return load_trades_payloads(_orderbook_loader_inputs(datasets))
    if payload_type == "simulation":
        return load_simulation_arrays_from_metadata(_simulation_loader_inputs(datasets))
    raise ValueError(f"Unsupported payload type for plot {plot_type}: {payload_type}")

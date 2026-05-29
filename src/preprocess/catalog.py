"""Catalog and payload helpers for dashboard-facing preprocess flows."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
import zipfile

import numpy as np

from src.dataset_artifacts import (
    DatasetLocator,
    detect_available_views as _detect_available_views,
    discover_preprocessed_artifacts,
    discover_simulation_artifacts,
    format_resolved_time as _format_resolved_time,
    format_time_step as _format_time_step,
)
from src.raw_batches import RawBatch, discover_raw_batches as _discover_raw_batches
from src.raw_batches import parse_timestamp

from .exceptions import (
    PreprocessValidationError,
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
)

PlotDatasetLocator = DatasetLocator
PreprocessedDataset = object
ViewSpecs = Sequence[tuple[str, Sequence[str]]]


def format_time_step(time_step: float | str | Decimal) -> str:
    try:
        return _format_time_step(time_step)
    except ValueError as error:
        raise PreprocessValidationError(str(error)) from error


def format_resolved_time(resolved_time: float | str | Decimal) -> str:
    try:
        return _format_resolved_time(resolved_time)
    except ValueError as error:
        raise PreprocessValidationError(str(error)) from error


def detect_available_views(
    path: Path,
    view_specs: ViewSpecs | None = None,
) -> tuple[str, ...]:
    return _detect_available_views(path, view_specs=view_specs)


def find_simulation_files(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
    resolved_time: float | None = None,
    resolved_time_token: str | None = None,
    algorithm_name: str | None = None,
) -> tuple[Path, ...]:
    return tuple(
        artifact.path
        for artifact in discover_simulation_artifacts(
            preprocessed_dir,
            product_id=product_id,
            timestamp=timestamp,
            time_step=time_step,
            time_step_token=time_step_token,
            resolved_time=resolved_time,
            resolved_time_token=resolved_time_token,
            algorithm_name=algorithm_name,
        )
    )


def has_simulation_file(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
) -> bool:
    return bool(
        find_simulation_files(
            preprocessed_dir,
            product_id,
            timestamp,
            time_step,
            time_step_token=time_step_token,
        )
    )


def discover_preprocessed_datasets(
    preprocessed_dir: Path,
    view_specs: ViewSpecs | None = None,
    simulation_view_keys: tuple[str, ...] = (
        "fill_probability",
        "mid_profit",
        "micro_profit",
        "mid_fill_probability_cost",
        "micro_fill_probability_cost",
    ),
):
    return discover_preprocessed_artifacts(
        preprocessed_dir,
        view_specs=view_specs,
        simulation_view_keys=simulation_view_keys,
    )


def discover_raw_batches(raw_dir: Path, preprocessed_dir: Path) -> list[RawBatch]:
    discovered = _discover_raw_batches(raw_dir)
    preprocessed_keys = {
        (dataset.product_id, dataset.timestamp)
        for dataset in discover_preprocessed_datasets(preprocessed_dir)
        if dataset.simulation_path is None
    }
    return [
        RawBatch(
            product_id=batch.product_id,
            timestamp=batch.timestamp,
            init_path=batch.init_path,
            updates_path=batch.updates_path,
            trade_path=batch.trade_path,
            is_preprocessed=(batch.product_id, batch.timestamp) in preprocessed_keys,
        )
        for batch in discovered
    ]


def load_preprocessed_payload(dataset) -> dict[str, object]:
    path = dataset.path
    cache = dataset.payload_cache if isinstance(dataset, DatasetLocator) else None
    if cache is not None and path in cache:
        return cache[path]

    try:
        with np.load(path, allow_pickle=False) as data:
            payload = {key: data[key] for key in data.files}
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataFileError(f"Failed to load {path.name}: {error}") from error

    _validate_preprocessed_payload_schema(payload, path)
    payload["product_id"] = dataset.product_id
    payload["timestamp"] = dataset.timestamp
    payload["time_step"] = dataset.time_step
    if hasattr(dataset, "available_views"):
        payload["available_views"] = dataset.available_views
    if cache is not None:
        cache[path] = payload
    return payload


def _validate_preprocessed_payload_schema(payload: dict[str, object], path: Path) -> None:
    required_fields = ("price_axis", "time_axis", "data", "bid", "ask")
    missing_fields = tuple(field for field in required_fields if field not in payload)
    if missing_fields:
        raise PreprocessedDataSchemaError(
            f"Preprocessed dataset {path.name} is missing required fields: {missing_fields}."
        )

    data = payload["data"]
    bid = payload["bid"]
    ask = payload["ask"]
    time_axis = payload["time_axis"]
    price_axis = payload["price_axis"]

    if time_axis.ndim != 1 or price_axis.ndim != 1:
        raise PreprocessedDataSchemaError(
            f"Preprocessed dataset {path.name} has invalid axis dimensionality."
        )
    if data.ndim != 2 or bid.ndim != 1 or ask.ndim != 1:
        raise PreprocessedDataSchemaError(
            f"Preprocessed dataset {path.name} has invalid data/bid/ask dimensionality."
        )
    if bid.shape != ask.shape:
        raise PreprocessedDataSchemaError(
            f"Preprocessed dataset {path.name} has mismatched bid/ask shapes."
        )
    if (
        data.shape[0] != time_axis.shape[0]
        or bid.shape[0] != time_axis.shape[0]
        or ask.shape[0] != time_axis.shape[0]
        or data.shape[1] != price_axis.shape[0]
    ):
        raise PreprocessedDataSchemaError(
            f"Preprocessed dataset {path.name} has incompatible data/bid/ask axis lengths."
        )

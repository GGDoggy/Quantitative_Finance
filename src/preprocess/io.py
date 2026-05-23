"""CSV/NPZ I/O helpers for preprocess discovery, payload loading, and context building."""
from __future__ import annotations

import csv
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from src.preprocess.adapters.plot_registry_detector import PlotRegistryViewDetector
from src.preprocess.exceptions import (
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
)
from src.preprocess.filenames import (
    match_preprocessed_filename,
    parse_simulation_filename,
)
from src.preprocess.models import PlotDatasetLocator, PreprocessContext, PreprocessedDataset, RawBatchLike


ViewDetector = Callable[[Iterable[str]], tuple[str, ...]]


def read_csv_rows(path: Path) -> list[list[float]]:
    with path.open(newline="") as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        return [list(row) for row in reader]


def build_context(batch: RawBatchLike, time_step: float) -> PreprocessContext:
    return PreprocessContext(
        batch=batch,
        time_step=time_step,
        init_rows=read_csv_rows(batch.init_path),
        updates_rows=read_csv_rows(batch.updates_path),
        trade_rows=read_csv_rows(batch.trade_path),
    )


def build_preprocess_context(batch: RawBatchLike, time_step: float) -> PreprocessContext:
    return build_context(batch, time_step)


def build_trade_arrays(
    trade_rows: list[list[float]],
    timestamp: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not trade_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        return empty_time, empty_float, empty_float, empty_float

    start_time = datetime.strptime(timestamp, "%Y%m%d.%H%M%S")
    midnight = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    trade_time = np.array(
        [midnight + timedelta(seconds=row[0]) for row in trade_rows],
        dtype="datetime64[ns]",
    )
    trade_price = np.array([row[1] for row in trade_rows], dtype=float)
    trade_volume = np.array([row[2] for row in trade_rows], dtype=float)
    trade_side = np.array([row[3] for row in trade_rows], dtype=float)
    return trade_time, trade_price, trade_volume, trade_side


def iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(
        entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix
    )


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    return iter_files(path, suffix)


def _default_view_detector(data_keys: Iterable[str]) -> tuple[str, ...]:
    from src.plots.registry import PLOT_REGISTRY

    detector = PlotRegistryViewDetector(PLOT_REGISTRY)
    return detector(data_keys)


def detect_available_views(
    path: Path,
    view_detector: ViewDetector | None = None,
) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" in data.files:
                available_views = tuple(str(view) for view in data["available_views"].tolist())
            else:
                data_keys = set(data.files)
                detector = view_detector or _default_view_detector
                available_views = detector(data_keys)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataFileError(f"Failed to inspect {path.name}: {error}") from error

    return available_views or ("orderbook",)


def _union_available_views(*view_groups: Iterable[str]) -> tuple[str, ...]:
    from src.plots.registry import PLOT_REGISTRY

    seen: set[str] = set()
    encountered: list[str] = []
    for view_group in view_groups:
        for view in view_group:
            if view in seen:
                continue
            seen.add(view)
            encountered.append(view)

    ordered_views = [view for view in PLOT_REGISTRY if view in seen]
    ordered_views.extend(view for view in encountered if view not in PLOT_REGISTRY)
    return tuple(ordered_views)


def load_preprocessed_payload(
    dataset: PreprocessedDataset | PlotDatasetLocator,
) -> dict[str, object]:
    path = dataset.path
    cache = dataset.payload_cache if isinstance(dataset, PlotDatasetLocator) else None
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
    if isinstance(dataset, PreprocessedDataset):
        payload["available_views"] = dataset.available_views
    if cache is not None:
        cache[path] = payload
    return payload


def _validate_preprocessed_payload_schema(
    payload: dict[str, object],
    path: Path,
) -> None:
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


def load_preprocessed_metadata(path: Path) -> tuple[str, str, float, str] | None:
    match = match_preprocessed_filename(path.name)
    if match is None:
        return None
    return (
        match.group("product_id"),
        match.group("timestamp"),
        float(match.group("time_step")),
        match.group("time_step"),
    )


def load_simulation_metadata(path: Path):
    return parse_simulation_filename(path.name)

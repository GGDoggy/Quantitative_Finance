"""Dataset discovery, filename parsing, and NPZ payload loading for preprocess."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Match
import zipfile

import numpy as np

from .exceptions import (
    PreprocessValidationError,
    PreprocessedDataError,
    PreprocessedDataFileError,
    PreprocessedDataSchemaError,
)
from .models import PlotDatasetLocator, PreprocessedDataset, RawBatch


DEFAULT_RESOLVED_TIME_FALLBACK = 1.0
TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
DEFAULT_VIEW_ORDER = (
    "orderbook",
    "trades_scatter",
    "trade_volume_timeline",
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)
DEFAULT_VIEW_SPECS: tuple[tuple[str, frozenset[str]], ...] = (
    ("orderbook", frozenset(("price_axis", "time_axis", "data", "bid", "ask"))),
    (
        "trades_scatter",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
    (
        "trade_volume_timeline",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
)
SIMULATION_VIEW_KEYS = (
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)

_RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_TRADE_RE = re.compile(
    r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})-orderbook_for_plot\.npz$"
)
_SIMULATION_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})"
    rf"(?:-resolved-(?P<resolved_time>{TIME_STEP_RE_FRAGMENT}))?"
    r"-simulation-(?P<algorithm>.+)\.npz$"
)

ViewSpecs = Sequence[tuple[str, Iterable[str]]]


@dataclass(frozen=True)
class SimulationFileMetadata:
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str
    resolved_time: float | None
    resolved_time_token: str | None
    algorithm_name: str


def format_time_step(time_step: float | str | Decimal) -> str:
    """Return a stable decimal representation for filenames and labels."""
    try:
        decimal_value = Decimal(str(time_step))
    except InvalidOperation as error:
        raise PreprocessValidationError(f"Invalid time step: {time_step!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise PreprocessValidationError(
            f"Time step must be a positive finite value: {time_step!r}"
        )

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d.%H%M%S")


def match_raw_level2_init_filename(filename: str) -> Match[str] | None:
    return _RAW_LEVEL2_INIT_RE.match(filename)


def match_raw_level2_updates_filename(filename: str) -> Match[str] | None:
    return _RAW_LEVEL2_UPDATES_RE.match(filename)


def match_raw_trade_filename(filename: str) -> Match[str] | None:
    return _RAW_TRADE_RE.match(filename)


def match_preprocessed_filename(filename: str) -> Match[str] | None:
    return _PREPROCESSED_RE.match(filename)


def match_simulation_filename(filename: str) -> Match[str] | None:
    return _SIMULATION_RE.match(filename)


def is_preprocessed_filename(filename: str) -> bool:
    return match_preprocessed_filename(filename) is not None


def is_simulation_filename(filename: str) -> bool:
    return match_simulation_filename(filename) is not None


def parse_simulation_filename(filename: str) -> SimulationFileMetadata | None:
    match = match_simulation_filename(filename)
    if not match:
        return None

    resolved_time_token = match.group("resolved_time")
    return SimulationFileMetadata(
        product_id=match.group("product_id"),
        timestamp=match.group("timestamp"),
        time_step=float(match.group("time_step")),
        time_step_token=match.group("time_step"),
        resolved_time=float(resolved_time_token) if resolved_time_token is not None else None,
        resolved_time_token=resolved_time_token,
        algorithm_name=match.group("algorithm"),
    )


def _simulation_time_step_tokens(
    time_step: float,
    time_step_token: str | None = None,
) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in (time_step_token, format_time_step(time_step), str(time_step)):
        if token is not None and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _simulation_value_tokens(
    value: float | None,
    value_token: str | None = None,
) -> tuple[str, ...]:
    if value is None:
        return ()

    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as error:
        raise PreprocessValidationError(f"Invalid resolved time: {value!r}") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise PreprocessValidationError(
            f"Resolved time must be a non-negative finite value: {value!r}"
        )

    normalized_value = decimal_value.normalize()
    if normalized_value == normalized_value.to_integral():
        formatted_value = format(normalized_value, "f")
    else:
        formatted_value = format(normalized_value, "f").rstrip("0").rstrip(".")

    tokens: list[str] = []
    for token in (value_token, formatted_value, str(value)):
        if token is not None and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _matches_resolved_time(
    metadata_resolved_time: float | None,
    metadata_resolved_time_token: str | None,
    resolved_time: float | None,
    resolved_time_tokens: set[str],
    resolved_time_fallback: float = DEFAULT_RESOLVED_TIME_FALLBACK,
) -> bool:
    if resolved_time is None:
        return True

    if metadata_resolved_time is None:
        return resolved_time == resolved_time_fallback

    return (
        metadata_resolved_time_token in resolved_time_tokens
        or metadata_resolved_time == resolved_time
    )


def iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(
        entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix
    )


def _normalized_view_specs(
    view_specs: ViewSpecs | None,
) -> tuple[tuple[str, frozenset[str]], ...]:
    if view_specs is None:
        return DEFAULT_VIEW_SPECS
    return tuple((view_key, frozenset(required_keys)) for view_key, required_keys in view_specs)


def detect_available_views(
    path: Path,
    view_specs: ViewSpecs | None = None,
) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" in data.files:
                available_views = tuple(str(view) for view in data["available_views"].tolist())
            else:
                data_keys = set(data.files)
                available_views = tuple(
                    view_key
                    for view_key, required_keys in _normalized_view_specs(view_specs)
                    if required_keys.issubset(data_keys)
                )
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataFileError(f"Failed to inspect {path.name}: {error}") from error

    return available_views or ("orderbook",)


def _union_available_views(
    *view_groups: Iterable[str],
    preferred_order: Sequence[str] = DEFAULT_VIEW_ORDER,
) -> tuple[str, ...]:
    seen: set[str] = set()
    encountered: list[str] = []
    for view_group in view_groups:
        for view in view_group:
            if view in seen:
                continue
            seen.add(view)
            encountered.append(view)

    ordered_views = [view for view in preferred_order if view in seen]
    ordered_views.extend(view for view in encountered if view not in preferred_order)
    return tuple(ordered_views)


def find_simulation_files(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
    resolved_time: float | None = None,
    resolved_time_token: str | None = None,
    algorithm_name: str | None = None,
    resolved_time_fallback: float = DEFAULT_RESOLVED_TIME_FALLBACK,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    time_step_tokens = set(_simulation_time_step_tokens(time_step, time_step_token))
    resolved_time_tokens = set(_simulation_value_tokens(resolved_time, resolved_time_token))

    for file_path in iter_files(preprocessed_dir, ".npz"):
        metadata = parse_simulation_filename(file_path.name)
        if metadata is None:
            continue
        if metadata.product_id != product_id or metadata.timestamp != timestamp:
            continue
        if not (
            metadata.time_step_token in time_step_tokens or metadata.time_step == time_step
        ):
            continue
        if algorithm_name is not None and metadata.algorithm_name != algorithm_name:
            continue
        if not _matches_resolved_time(
            metadata.resolved_time,
            metadata.resolved_time_token,
            resolved_time,
            resolved_time_tokens,
            resolved_time_fallback=resolved_time_fallback,
        ):
            continue
        candidates.append(file_path)

    return tuple(sorted(candidates))


def has_simulation_file(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
    resolved_time_fallback: float = DEFAULT_RESOLVED_TIME_FALLBACK,
) -> bool:
    return bool(
        find_simulation_files(
            preprocessed_dir,
            product_id,
            timestamp,
            time_step,
            time_step_token,
            resolved_time_fallback=resolved_time_fallback,
        )
    )


def discover_preprocessed_datasets(
    preprocessed_dir: Path,
    view_specs: ViewSpecs | None = None,
    simulation_view_keys: tuple[str, ...] = SIMULATION_VIEW_KEYS,
) -> list[PreprocessedDataset]:
    entries: dict[tuple[str, str, float], dict[str, object]] = {}

    for file_path in iter_files(preprocessed_dir, ".npz"):
        preprocessed_match = match_preprocessed_filename(file_path.name)
        simulation_metadata = parse_simulation_filename(file_path.name)
        if not preprocessed_match and simulation_metadata is None:
            continue

        if preprocessed_match:
            product_id = preprocessed_match.group("product_id")
            timestamp = preprocessed_match.group("timestamp")
            time_step = float(preprocessed_match.group("time_step"))
            time_step_token = preprocessed_match.group("time_step")
        else:
            assert simulation_metadata is not None
            product_id = simulation_metadata.product_id
            timestamp = simulation_metadata.timestamp
            time_step = simulation_metadata.time_step
            time_step_token = simulation_metadata.time_step_token

        key = (product_id, timestamp, time_step)
        entry = entries.setdefault(
            key,
            {
                "product_id": product_id,
                "timestamp": timestamp,
                "time_step": time_step,
                "time_step_token": time_step_token,
                "orderbook_path": None,
                "simulation_paths": [],
                "simulation_metadata": {},
                "orderbook_views": (),
            },
        )

        if preprocessed_match:
            try:
                available_views = detect_available_views(file_path, view_specs=view_specs)
            except PreprocessedDataError:
                continue
            entry["orderbook_path"] = file_path
            entry["time_step_token"] = time_step_token
            entry["orderbook_views"] = _union_available_views(
                available_views,
                preferred_order=DEFAULT_VIEW_ORDER,
            )
            continue

        simulation_paths = entry["simulation_paths"]
        if isinstance(simulation_paths, list):
            simulation_paths.append(file_path)
        simulation_metadata_by_name = entry["simulation_metadata"]
        if isinstance(simulation_metadata_by_name, dict) and simulation_metadata is not None:
            simulation_metadata_by_name[file_path.name] = simulation_metadata

    datasets: list[PreprocessedDataset] = []
    for entry in entries.values():
        orderbook_path = entry["orderbook_path"]
        simulation_paths = sorted(
            path for path in entry["simulation_paths"] if isinstance(path, Path)
        )
        simulation_metadata_by_name = entry["simulation_metadata"]
        orderbook_views = tuple(entry["orderbook_views"])
        time_step_token = str(entry["time_step_token"])

        if isinstance(orderbook_path, Path) and not simulation_paths:
            datasets.append(
                PreprocessedDataset(
                    product_id=str(entry["product_id"]),
                    timestamp=str(entry["timestamp"]),
                    time_step=float(entry["time_step"]),
                    path=orderbook_path,
                    available_views=orderbook_views,
                    time_step_token=time_step_token,
                )
            )
            continue

        for simulation_path in simulation_paths:
            simulation_metadata = None
            if isinstance(simulation_metadata_by_name, dict):
                simulation_metadata = simulation_metadata_by_name.get(simulation_path.name)
            base_views = orderbook_views if isinstance(orderbook_path, Path) else ()
            datasets.append(
                PreprocessedDataset(
                    product_id=str(entry["product_id"]),
                    timestamp=str(entry["timestamp"]),
                    time_step=float(entry["time_step"]),
                    path=orderbook_path if isinstance(orderbook_path, Path) else simulation_path,
                    available_views=_union_available_views(
                        base_views,
                        simulation_view_keys,
                        preferred_order=DEFAULT_VIEW_ORDER,
                    ),
                    time_step_token=time_step_token,
                    resolved_time=(
                        simulation_metadata.resolved_time
                        if isinstance(simulation_metadata, SimulationFileMetadata)
                        else None
                    ),
                    resolved_time_token=(
                        simulation_metadata.resolved_time_token
                        if isinstance(simulation_metadata, SimulationFileMetadata)
                        else None
                    ),
                    algorithm_name=(
                        simulation_metadata.algorithm_name
                        if isinstance(simulation_metadata, SimulationFileMetadata)
                        else None
                    ),
                    simulation_path=simulation_path,
                )
            )

    datasets.sort(
        key=lambda dataset: (
            dataset.product_id,
            dataset.timestamp,
            dataset.time_step,
            dataset.simulation_path.name if dataset.simulation_path is not None else "",
        )
    )
    return datasets


def discover_raw_batches(raw_dir: Path, preprocessed_dir: Path) -> list[RawBatch]:
    entries: dict[tuple[str, str], dict[str, Path]] = {}

    for file_path in iter_files(raw_dir, ".csv"):
        name = file_path.name
        match = match_raw_level2_init_filename(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["init"] = file_path
            continue

        match = match_raw_level2_updates_filename(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["updates"] = file_path
            continue

        match = match_raw_trade_filename(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["trade"] = file_path

    preprocessed_keys = {
        (dataset.product_id, dataset.timestamp)
        for dataset in discover_preprocessed_datasets(preprocessed_dir)
        if match_preprocessed_filename(dataset.path.name)
    }

    batches: list[RawBatch] = []
    for (product_id, timestamp), parts in sorted(entries.items()):
        if {"init", "updates", "trade"} - set(parts):
            continue
        batches.append(
            RawBatch(
                product_id=product_id,
                timestamp=timestamp,
                init_path=parts["init"],
                updates_path=parts["updates"],
                trade_path=parts["trade"],
                is_preprocessed=(product_id, timestamp) in preprocessed_keys,
            )
        )

    return batches


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

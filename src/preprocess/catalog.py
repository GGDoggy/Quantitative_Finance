"""Catalog raw Coinbase CSV batches and preprocessed plot datasets."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import zipfile
from typing import Iterable, MutableMapping

import numpy as np

from src.plots.errors import PreprocessedDataError
from src.plots.registry import PLOT_REGISTRY


SIMULATION_VIEW_KEY = "fill_probability"


RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
RAW_TRADE_RE = re.compile(r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$")
TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})-orderbook_for_plot\.npz$"
)
SIMULATION_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT}).*simulation.*\.npz$"
)


def format_time_step(time_step: float | str | Decimal) -> str:
    """Return a stable decimal representation for filenames and labels."""
    try:
        decimal_value = Decimal(str(time_step))
    except InvalidOperation as error:
        raise ValueError(f"Invalid time step: {time_step!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"Time step must be a positive finite value: {time_step!r}")

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def _simulation_time_step_tokens(
    time_step: float,
    time_step_token: str | None = None,
) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in (time_step_token, format_time_step(time_step), str(time_step)):
        if token is not None and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def find_simulation_files(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    time_step_tokens = set(_simulation_time_step_tokens(time_step, time_step_token))

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        match = SIMULATION_RE.match(file_path.name)
        if not match:
            continue
        if (
            match.group("product_id") != product_id
            or match.group("timestamp") != timestamp
        ):
            continue

        matched_time_step = match.group("time_step")
        if matched_time_step in time_step_tokens or float(matched_time_step) == time_step:
            candidates.append(file_path)

    return tuple(sorted(candidates))


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
            time_step_token,
        )
    )


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d.%H%M%S")


@dataclass(frozen=True)
class RawBatch:
    product_id: str
    timestamp: str
    init_path: Path
    updates_path: Path
    trade_path: Path
    is_preprocessed: bool = False

    @property
    def batch_id(self) -> str:
        return f"{self.product_id}|{self.timestamp}"

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        suffix = " | preprocessed" if self.is_preprocessed else ""
        return f"{self.product_id} | {formatted}{suffix}"


@dataclass(frozen=True)
class PlotDatasetLocator:
    product_id: str
    timestamp: str
    time_step: float
    preprocessed_dir: Path
    time_step_token: str | None = None
    original_path: Path | None = None
    simulation_path: Path | None = None
    payload_cache: MutableMapping[Path, dict[str, object]] | None = field(
        default=None,
        compare=False,
        hash=False,
        repr=False,
    )

    @property
    def base_id(self) -> str:
        time_step_token = self.time_step_token or format_time_step(self.time_step)
        return f"{self.product_id}-{self.timestamp}-{time_step_token}"

    @property
    def path(self) -> Path:
        if self.original_path is not None:
            return self.original_path
        return self.preprocessed_dir / f"{self.base_id}-orderbook_for_plot.npz"


@dataclass(frozen=True)
class PreprocessedDataset:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]
    time_step_token: str | None = None
    simulation_path: Path | None = None

    @property
    def dataset_id(self) -> str:
        if self.simulation_path is not None:
            return f"{self.path}#{self.simulation_path.name}"
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views)
        simulation_suffix = (
            f" | {self.simulation_path.stem}"
            if self.simulation_path is not None
            else ""
        )
        return (
            f"{self.product_id} | {formatted} | {format_time_step(self.time_step)}s"
            f"{simulation_suffix} | {views}"
        )

    def to_locator(
        self,
        preprocessed_dir: Path,
        payload_cache: MutableMapping[Path, dict[str, object]] | None = None,
    ) -> PlotDatasetLocator:
        return PlotDatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            time_step=self.time_step,
            preprocessed_dir=preprocessed_dir,
            time_step_token=self.time_step_token,
            original_path=self.path,
            simulation_path=self.simulation_path,
            payload_cache=payload_cache,
        )


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(
        entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix
    )


def detect_available_views(
    path: Path,
    dataset_hint: PlotDatasetLocator | None = None,
) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" in data.files:
                available_views = tuple(str(view) for view in data["available_views"].tolist())
            else:
                data_keys = set(data.files)
                available_views = tuple(
                    key
                    for key, spec in PLOT_REGISTRY.items()
                    if set(spec.required_payload_keys).issubset(data_keys)
                )
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(f"Failed to inspect {path.name}: {error}") from error

    if (
        dataset_hint is not None
        and SIMULATION_VIEW_KEY in PLOT_REGISTRY
        and has_simulation_file(
            dataset_hint.preprocessed_dir,
            dataset_hint.product_id,
            dataset_hint.timestamp,
            dataset_hint.time_step,
            dataset_hint.time_step_token,
        )
        and SIMULATION_VIEW_KEY not in available_views
    ):
        available_views = (*available_views, SIMULATION_VIEW_KEY)

    return available_views or ("orderbook",)


def _union_available_views(*view_groups: Iterable[str]) -> tuple[str, ...]:
    views: set[str] = set()
    for view_group in view_groups:
        views.update(view_group)

    ordered_views = [view for view in PLOT_REGISTRY if view in views]
    ordered_views.extend(sorted(views - set(ordered_views)))
    return tuple(ordered_views)


def discover_preprocessed_datasets(preprocessed_dir: Path) -> list[PreprocessedDataset]:
    entries: dict[
        tuple[str, str, float],
        dict[str, object],
    ] = {}

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        preprocessed_match = PREPROCESSED_RE.match(file_path.name)
        simulation_match = SIMULATION_RE.match(file_path.name)
        match = preprocessed_match or simulation_match
        if not match:
            continue

        product_id = match.group("product_id")
        timestamp = match.group("timestamp")
        time_step = float(match.group("time_step"))
        time_step_token = match.group("time_step")
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
                "orderbook_views": (),
            },
        )

        if preprocessed_match:
            locator = PlotDatasetLocator(
                product_id=product_id,
                timestamp=timestamp,
                time_step=time_step,
                preprocessed_dir=preprocessed_dir,
                time_step_token=time_step_token,
                original_path=file_path,
            )

            try:
                available_views = detect_available_views(file_path, locator)
            except PreprocessedDataError:
                continue

            entry["orderbook_path"] = file_path
            entry["time_step_token"] = time_step_token
            entry["orderbook_views"] = _union_available_views(available_views)
            continue

        simulation_paths = entry["simulation_paths"]
        if isinstance(simulation_paths, list):
            simulation_paths.append(file_path)

    datasets: list[PreprocessedDataset] = []
    for entry in entries.values():
        orderbook_path = entry["orderbook_path"]
        simulation_paths = sorted(
            path for path in entry["simulation_paths"] if isinstance(path, Path)
        )
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
            base_views = orderbook_views if isinstance(orderbook_path, Path) else ()
            datasets.append(
                PreprocessedDataset(
                    product_id=str(entry["product_id"]),
                    timestamp=str(entry["timestamp"]),
                    time_step=float(entry["time_step"]),
                    path=(
                        orderbook_path if isinstance(orderbook_path, Path) else simulation_path
                    ),
                    available_views=_union_available_views(
                        base_views,
                        (SIMULATION_VIEW_KEY,),
                    ),
                    time_step_token=time_step_token,
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

    for file_path in _iter_files(raw_dir, ".csv"):
        name = file_path.name
        match = RAW_LEVEL2_INIT_RE.match(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["init"] = file_path
            continue

        match = RAW_LEVEL2_UPDATES_RE.match(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["updates"] = file_path
            continue

        match = RAW_TRADE_RE.match(name)
        if match:
            key = (match.group("product_id"), match.group("timestamp"))
            entries.setdefault(key, {})["trade"] = file_path

    preprocessed_keys = {
        (dataset.product_id, dataset.timestamp)
        for dataset in discover_preprocessed_datasets(preprocessed_dir)
        if PREPROCESSED_RE.match(dataset.path.name)
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
        raise PreprocessedDataError(f"Failed to load {path.name}: {error}") from error

    payload["product_id"] = dataset.product_id
    payload["timestamp"] = dataset.timestamp
    payload["time_step"] = dataset.time_step
    if isinstance(dataset, PreprocessedDataset):
        payload["available_views"] = dataset.available_views
    if cache is not None:
        cache[path] = payload
    return payload

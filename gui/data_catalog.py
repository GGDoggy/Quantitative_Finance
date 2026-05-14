from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import zipfile
from typing import Iterable

import numpy as np

from gui.registry import PLOT_REGISTRY


RAW_LEVEL2_INIT_RE = re.compile(r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$")
RAW_LEVEL2_UPDATES_RE = re.compile(r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$")
RAW_TRADE_RE = re.compile(r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$")
PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    r"(?P<time_step>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)-orderbook_for_plot\.npz$"
)


class PreprocessedDataError(RuntimeError):
    pass


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

    @property
    def base_id(self) -> str:
        return f"{self.product_id}-{self.timestamp}-{format_time_step(self.time_step)}"

    @property
    def path(self) -> Path:
        return self.preprocessed_dir / f"{self.base_id}-orderbook_for_plot.npz"


@dataclass(frozen=True)
class PreprocessedDataset:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]

    @property
    def dataset_id(self) -> str:
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views)
        return f"{self.product_id} | {formatted} | {format_time_step(self.time_step)}s | {views}"

    def to_locator(self, preprocessed_dir: Path) -> PlotDatasetLocator:
        return PlotDatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            time_step=self.time_step,
            preprocessed_dir=preprocessed_dir,
        )


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix)


def detect_available_views(path: Path) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" in data.files:
                return tuple(str(view) for view in data["available_views"].tolist())
            data_keys = set(data.files)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(f"Failed to inspect {path.name}: {error}") from error

    available_views = tuple(
        key
        for key, spec in PLOT_REGISTRY.items()
        if set(spec.required_payload_keys).issubset(data_keys)
    )
    return available_views or ("orderbook",)


def discover_preprocessed_datasets(preprocessed_dir: Path) -> list[PreprocessedDataset]:
    datasets: list[PreprocessedDataset] = []

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        match = PREPROCESSED_RE.match(file_path.name)
        if not match:
            continue

        try:
            available_views = detect_available_views(file_path)
        except PreprocessedDataError:
            continue

        datasets.append(
            PreprocessedDataset(
                product_id=match.group("product_id"),
                timestamp=match.group("timestamp"),
                time_step=float(match.group("time_step")),
                path=file_path,
                available_views=available_views,
            )
        )

    datasets.sort(key=lambda dataset: (dataset.product_id, dataset.timestamp, dataset.time_step))
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


def load_preprocessed_payload(dataset: PreprocessedDataset | PlotDatasetLocator) -> dict[str, object]:
    try:
        with np.load(dataset.path, allow_pickle=False) as data:
            payload = {key: data[key] for key in data.files}
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(f"Failed to load {dataset.path.name}: {error}") from error

    payload["product_id"] = dataset.product_id
    payload["timestamp"] = dataset.timestamp
    payload["time_step"] = dataset.time_step
    if isinstance(dataset, PreprocessedDataset):
        payload["available_views"] = dataset.available_views
    return payload

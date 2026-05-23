"""Catalog raw Coinbase CSV batches and preprocessed plot datasets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable
import zipfile

import numpy as np

from src.plotlib.errors import PreprocessedDataError
from src.plotlib.discovery import (
    SimulationFileMetadata,
    find_simulation_files,
    format_time_step,
    parse_simulation_filename,
)

DEFAULT_PREPROCESSED_VIEW_TOKENS = (
    "orderbook",
    "trades_scatter",
    "trade_volume_timeline",
)


PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    r"(?P<time_step>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)-orderbook_for_plot\.npz$"
)


RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
RAW_TRADE_RE = re.compile(r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$")
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
class PreprocessedDataset:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]
    time_step_token: str | None = None
    resolved_time: float | None = None
    resolved_time_token: str | None = None
    algorithm_name: str | None = None
    simulation_path: Path | None = None

    @property
    def dataset_id(self) -> str:
        if self.simulation_path is not None:
            return f"{self.path}#{self.simulation_path.name}"
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views) or "none"
        simulation_suffix = (
            f" | {self.simulation_path.stem}"
            if self.simulation_path is not None
            else ""
        )
        return (
            f"{self.product_id} | {formatted} | {format_time_step(self.time_step)}s"
            f"{simulation_suffix} | {views}"
        )


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(
        entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix
    )


def _read_dataset_capabilities(path: Path) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" not in data.files:
                return DEFAULT_PREPROCESSED_VIEW_TOKENS
            return tuple(str(view) for view in data["available_views"].tolist())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(f"Failed to inspect {path.name}: {error}") from error



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


def _union_available_views(*view_groups: Iterable[str]) -> tuple[str, ...]:
    views: set[str] = set()
    for view_group in view_groups:
        views.update(view_group)

    ordered_views = [
        view for view in DEFAULT_PREPROCESSED_VIEW_TOKENS if view in views
    ]
    ordered_views.extend(
        sorted(view for view in views if view not in set(ordered_views))
    )
    return tuple(ordered_views)


def discover_preprocessed_datasets(preprocessed_dir: Path) -> list[PreprocessedDataset]:
    entries: dict[
        tuple[str, str, float],
        dict[str, object],
    ] = {}

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        preprocessed_match = PREPROCESSED_RE.match(file_path.name)
        simulation_metadata = parse_simulation_filename(file_path.name)
        simulation_match = simulation_metadata is not None
        if not preprocessed_match and not simulation_match:
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
                available_views = _read_dataset_capabilities(file_path)
            except PreprocessedDataError:
                continue

            entry["orderbook_path"] = file_path
            entry["time_step_token"] = time_step_token
            entry["orderbook_views"] = _union_available_views(available_views)
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
                    path=(
                        orderbook_path if isinstance(orderbook_path, Path) else simulation_path
                    ),
                    available_views=base_views,
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

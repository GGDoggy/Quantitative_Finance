"""Catalog raw Coinbase CSV batches and preprocessed plot datasets."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from src.preprocess.exceptions import PreprocessedDataError
from src.preprocess.filenames import (
    DEFAULT_RESOLVED_TIME_FALLBACK,
    SimulationFileMetadata,
    _matches_resolved_time,
    _simulation_time_step_tokens,
    _simulation_value_tokens,
    match_preprocessed_filename,
    match_raw_level2_init_filename,
    match_raw_level2_updates_filename,
    match_raw_trade_filename,
    parse_simulation_filename,
)
from src.preprocess.io import (
    _union_available_views,
    detect_available_views,
    iter_files,
)
from src.preprocess.models import PlotDatasetLocator, PreprocessedDataset, RawBatch


ViewDetector = Callable[[Iterable[str]], tuple[str, ...]]

SIMULATION_VIEW_KEYS = (
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)


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
        if (
            metadata.product_id != product_id
            or metadata.timestamp != timestamp
        ):
            continue

        if not (
            metadata.time_step_token in time_step_tokens
            or metadata.time_step == time_step
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
    view_detector: ViewDetector | None = None,
    simulation_view_keys: tuple[str, ...] = SIMULATION_VIEW_KEYS,
) -> list[PreprocessedDataset]:
    entries: dict[
        tuple[str, str, float],
        dict[str, object],
    ] = {}

    for file_path in iter_files(preprocessed_dir, ".npz"):
        preprocessed_match = match_preprocessed_filename(file_path.name)
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
                available_views = detect_available_views(file_path, view_detector=view_detector)
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
                    available_views=_union_available_views(
                        base_views,
                        simulation_view_keys,
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

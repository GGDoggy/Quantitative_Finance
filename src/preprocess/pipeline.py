"""Preprocess pipeline for converting raw batches into dashboard datasets."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import tempfile
from typing import Protocol

import numpy as np

from src.dataset_artifacts import (
    PreprocessedArtifact as PreprocessedDataset,
    build_preprocessed_output_path,
    discover_preprocessed_artifacts,
)
from src.raw_batches import LoadedRawBatch, RawBatch, load_raw_batch, parse_timestamp

from .exceptions import PreprocessOutputConflictError
from .orderbook import build_orderbook_payload


DEFAULT_TIME_STEP = 0.01


@dataclass(frozen=True)
class PreprocessContext:
    batch: RawBatch
    time_step: float
    init_rows: list[list[float]]
    updates_rows: list[list[float]]
    trade_rows: list[list[float]]


@dataclass(frozen=True)
class PreprocessBuilderSpec:
    preprocess_builder: Callable[[PreprocessContext], dict[str, object]] | None
    required_payload_keys: tuple[str, ...]


class BuilderSpec(Protocol):
    preprocess_builder: Callable[[PreprocessContext], dict[str, object]] | None
    required_payload_keys: tuple[str, ...]


def build_trade_arrays(
    trade_rows: list[list[float]],
    timestamp: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not trade_rows:
        empty_time = np.array([], dtype="datetime64[ns]")
        empty_float = np.array([], dtype=float)
        return empty_time, empty_float, empty_float, empty_float

    start_time = parse_timestamp(timestamp)
    midnight = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    trade_time = np.array(
        [midnight + timedelta(seconds=row[0]) for row in trade_rows],
        dtype="datetime64[ns]",
    )
    trade_price = np.array([row[1] for row in trade_rows], dtype=float)
    trade_volume = np.array([row[2] for row in trade_rows], dtype=float)
    trade_side = np.array([row[3] for row in trade_rows], dtype=float)
    return trade_time, trade_price, trade_volume, trade_side


def build_trade_payload(context: PreprocessContext) -> dict[str, object]:
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(
        context.trade_rows,
        context.batch.timestamp,
    )
    return {
        "trade_time": trade_time,
        "trade_price": trade_price,
        "trade_volume": trade_volume,
        "trade_side": trade_side,
    }


PLOT_REGISTRY: dict[str, PreprocessBuilderSpec] = {
    "orderbook": PreprocessBuilderSpec(
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
    ),
    "trades_scatter": PreprocessBuilderSpec(
        preprocess_builder=build_trade_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "trade_volume_timeline": PreprocessBuilderSpec(
        preprocess_builder=build_trade_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
}


def get_default_builder_registry() -> Mapping[str, BuilderSpec]:
    return PLOT_REGISTRY


def build_context(batch: RawBatch, time_step: float) -> PreprocessContext:
    loaded_batch = load_raw_batch(batch)
    return build_preprocess_context(batch, time_step, loaded_batch=loaded_batch)


def build_preprocess_context(
    batch: RawBatch,
    time_step: float,
    *,
    loaded_batch: LoadedRawBatch | None = None,
) -> PreprocessContext:
    loaded = loaded_batch or load_raw_batch(batch)
    return PreprocessContext(
        batch=batch,
        time_step=time_step,
        init_rows=loaded.init,
        updates_rows=loaded.updates,
        trade_rows=loaded.trades,
    )


def _merge_payload_chunk(base_payload: dict[str, object], chunk: dict[str, object]) -> None:
    for key, value in chunk.items():
        if key not in base_payload:
            base_payload[key] = value
            continue

        existing = base_payload[key]
        if isinstance(existing, np.ndarray) and isinstance(value, np.ndarray):
            if existing.shape != value.shape or not np.array_equal(
                existing,
                value,
                equal_nan=True,
            ):
                raise PreprocessOutputConflictError(
                    f"Conflicting preprocess outputs for key '{key}'."
                )
            continue

        if existing != value:
            raise PreprocessOutputConflictError(
                f"Conflicting preprocess outputs for key '{key}'."
            )


def preprocess_batch(
    batch: RawBatch,
    output_dir: Path,
    time_step: float = DEFAULT_TIME_STEP,
    builder_registry: Mapping[str, BuilderSpec] | None = None,
) -> PreprocessedDataset:
    context = build_context(batch, time_step)
    payload: dict[str, object] = {}
    available_views: list[str] = []
    registry = get_default_builder_registry() if builder_registry is None else builder_registry

    for plot_key, spec in registry.items():
        if spec.preprocess_builder is None:
            continue
        chunk = spec.preprocess_builder(context)
        if not all(required_key in chunk for required_key in spec.required_payload_keys):
            continue
        _merge_payload_chunk(payload, chunk)
        available_views.append(plot_key)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_preprocessed_output_path(
        output_dir,
        batch.product_id,
        batch.timestamp,
        time_step,
    )
    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        prefix=output_path.stem + "-",
        suffix=".npz",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        np.savez_compressed(
            temp_path,
            **payload,
            available_views=np.array(available_views),
        )
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    for dataset in discover_preprocessed_artifacts(output_dir):
        if dataset.path == output_path and dataset.simulation_path is None:
            return dataset

    raise FileNotFoundError(f"Failed to discover freshly written dataset: {output_path}")


def preprocess_batches(
    batches: list[RawBatch],
    output_dir: Path,
    time_step: float = DEFAULT_TIME_STEP,
    builder_registry: Mapping[str, BuilderSpec] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[PreprocessedDataset]:
    results: list[PreprocessedDataset] = []
    total = len(batches)

    for index, batch in enumerate(batches, start=1):
        if progress_callback is not None:
            progress_callback(f"[{index}/{total}] preprocessing {batch.display_name}")
        results.append(
            preprocess_batch(
                batch,
                output_dir=output_dir,
                time_step=time_step,
                builder_registry=builder_registry,
            )
        )

    if progress_callback is not None and batches:
        progress_callback(f"Finished preprocessing {len(batches)} batch(es).")

    return results

"""Coordinate registered preprocess builders and write dashboard-ready datasets."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import tempfile
from typing import Callable, Protocol

import numpy as np

from src.dataset_artifacts import (
    build_preprocessed_output_path,
    discover_preprocessed_artifacts,
)
from src.raw_batches import LoadedRawBatch, RawBatch, load_raw_batch

from .exceptions import PreprocessOutputConflictError
from .models import PreprocessContext, PreprocessedDataset
from .registry import PLOT_REGISTRY


DEFAULT_TIME_STEP = 0.01


class BuilderSpec(Protocol):
    preprocess_builder: Callable[[PreprocessContext], dict[str, object]] | None
    required_payload_keys: tuple[str, ...]


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

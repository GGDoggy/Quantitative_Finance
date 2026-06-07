"""Preprocess pipeline for converting raw batches into dashboard datasets."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

import numpy as np

from src.dataset_artifacts import (
    PreprocessedArtifact as PreprocessedDataset,
    build_preprocessed_output_path,
    discover_preprocessed_artifacts,
)
from src.raw_batches import LoadedRawBatch, RawBatch, load_raw_batch

from .exceptions import PreprocessValidationError
from .orderbook import build_orderbook_payload
from .trade import build_trade_payload


DEFAULT_DEPTH = 10
PREPROCESS_TIMEZONE = ZoneInfo("Asia/Taipei")


@dataclass(frozen=True)
class PreprocessContext:
    batch: RawBatch
    depth: int
    start_time: float
    init_rows: list[list[float]]
    updates_rows: list[list[float]]
    trades_rows: list[list[float]]


@dataclass(frozen=True)
class PreprocessBuilderSpec:
    preprocess_type: str
    preprocess_builder: Callable[[PreprocessContext], dict[str, object]] | None
    required_payload_keys: tuple[str, ...]
    available_views: tuple[str, ...]


PLOT_REGISTRY: dict[str, PreprocessBuilderSpec] = {
    "orderbook": PreprocessBuilderSpec(
        preprocess_type="orderbook",
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
        available_views=("orderbook",),
    ),
    "trade": PreprocessBuilderSpec(
        preprocess_type="trade",
        preprocess_builder=build_trade_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
        available_views=("trades_scatter", "trade_volume_timeline"),
    ),
}


def generate_preprocess_timestamp() -> str:
    now = datetime.now(PREPROCESS_TIMEZONE)
    return f"{now.strftime('%Y%m%d.%H%M%S')}.{now.microsecond // 1000:03d}"


def _validate_depth(depth: int) -> int:
    if not isinstance(depth, int) or depth <= 0:
        raise PreprocessValidationError("Preprocess depth must be a positive integer.")
    return depth


def build_preprocess_context(
    batch: RawBatch,
    depth: int,
    *,
    loaded_batch: LoadedRawBatch | None = None,
) -> PreprocessContext:
    loaded = loaded_batch or load_raw_batch(batch)
    return PreprocessContext(
        batch=batch,
        depth=_validate_depth(depth),
        start_time=loaded.start_time,
        init_rows=loaded.init,
        updates_rows=loaded.updates,
        trades_rows=loaded.trades,
    )


def _save_preprocess_payload(
    *,
    context: PreprocessContext,
    output_dir: Path,
    preprocess_type: str,
    payload: Mapping[str, object],
    available_views: tuple[str, ...],
    preprocess_timestamp: str,
    seq_num: int,
) -> PreprocessedDataset:
    output_path = build_preprocessed_output_path(
        output_dir,
        preprocess_type=preprocess_type,
        preprocess_timestamp=preprocess_timestamp,
        seq_num=seq_num,
    )
    metadata: dict[str, object] = {
        "preprocess_type": preprocess_type,
        "preprocess_timestamp": preprocess_timestamp,
        "seq_num": int(seq_num),
        "product_id": context.batch.product_id,
        "timestamp": context.batch.timestamp,
        "file_stem": context.batch.file_stem,
        "available_views": np.asarray(available_views),
    }
    if preprocess_type == "orderbook":
        metadata["depth"] = int(context.depth)

    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        prefix=output_path.stem + "-",
        suffix=".npz",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        np.savez_compressed(temp_path, **payload, **metadata)
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    for dataset in discover_preprocessed_artifacts(output_dir):
        if dataset.path == output_path and dataset.simulation_path is None:
            return dataset

    raise FileNotFoundError(f"Failed to discover freshly written dataset: {output_path}")


def preprocess_batch(
    batch: RawBatch,
    output_dir: Path,
    depth: int = DEFAULT_DEPTH,
    builder_registry: Mapping[str, PreprocessBuilderSpec] | None = None,
    preprocess_timestamp: str | None = None,
    seq_num: int = 0,
) -> list[PreprocessedDataset]:
    context = build_preprocess_context(batch, depth)
    registry = PLOT_REGISTRY if builder_registry is None else builder_registry
    preprocess_timestamp = preprocess_timestamp or generate_preprocess_timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets: list[PreprocessedDataset] = []

    for spec in registry.values():
        if spec.preprocess_builder is None:
            continue
        payload = spec.preprocess_builder(context)
        if not all(required_key in payload for required_key in spec.required_payload_keys):
            continue
        datasets.append(
            _save_preprocess_payload(
                context=context,
                output_dir=output_dir,
                preprocess_type=spec.preprocess_type,
                payload=payload,
                available_views=spec.available_views,
                preprocess_timestamp=preprocess_timestamp,
                seq_num=seq_num,
            )
        )

    return datasets


def preprocess_batches(
    batches: list[RawBatch],
    output_dir: Path,
    depth: int = DEFAULT_DEPTH,
    builder_registry: Mapping[str, PreprocessBuilderSpec] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[PreprocessedDataset]:
    results: list[PreprocessedDataset] = []
    total = len(batches)
    preprocess_timestamp = generate_preprocess_timestamp()

    for index, batch in enumerate(batches, start=1):
        if progress_callback is not None:
            progress_callback(f"[{index}/{total}] preprocessing {batch.display_name}")
        results.extend(
            preprocess_batch(
                batch,
                output_dir=output_dir,
                depth=depth,
                builder_registry=builder_registry,
                preprocess_timestamp=preprocess_timestamp,
                seq_num=index - 1,
            )
        )

    if progress_callback is not None and batches:
        progress_callback(f"Finished preprocessing {len(batches)} batch(es).")

    return results

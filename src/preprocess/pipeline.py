"""Preprocess pipeline for converting raw batches into dashboard datasets."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import tempfile

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


@dataclass(frozen=True)
class PreprocessContext:
    batch: RawBatch
    depth: int
    trade_window_seconds: int
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
        required_payload_keys=(),
        available_views=("orderbook",),
    ),
    "trade": PreprocessBuilderSpec(
        preprocess_type="trade",
        preprocess_builder=build_trade_payload,
        required_payload_keys=(),
        available_views=("trades_scatter", "trade_volume_timeline"),
    ),
}


def _validate_depth(depth: int) -> int:
    if not isinstance(depth, int) or depth <= 0:
        raise PreprocessValidationError("Preprocess depth must be a positive integer.")
    return depth


def _validate_trade_window_seconds(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreprocessValidationError(
            "trade_window_seconds must be a positive integer."
        )
    return value


def build_preprocess_context(
    batch: RawBatch,
    depth: int,
    *,
    loaded_batch: LoadedRawBatch | None = None,
    trade_window_seconds: int = 1,
) -> PreprocessContext:
    loaded = loaded_batch or load_raw_batch(batch)
    return PreprocessContext(
        batch=batch,
        depth=_validate_depth(depth),
        trade_window_seconds=_validate_trade_window_seconds(trade_window_seconds),
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
) -> PreprocessedDataset:
    output_path = build_preprocessed_output_path(
        output_dir,
        preprocess_type=preprocess_type,
        preprocess_timestamp=preprocess_timestamp,
    )
    metadata: dict[str, object] = {
        "preprocess_type": preprocess_type,
        "preprocess_timestamp": preprocess_timestamp,
        "product_id": context.batch.product_id,
        "timestamp": context.batch.timestamp,
        "file_stem": context.batch.file_stem,
        "available_views": np.asarray(available_views),
    }
    if preprocess_type == "orderbook":
        metadata["depth"] = int(context.depth)

    merged_payload: dict[str, object]
    if preprocess_type == "trade":
        existing_payload = _load_existing_npz(output_path)
        merged_payload = _merge_trade_payload(existing_payload, payload, metadata)
    elif preprocess_type == "orderbook":
        existing_payload = _load_existing_npz(output_path)
        merged_payload = _merge_orderbook_payload(existing_payload, payload, metadata)
    else:
        merged_payload = dict(payload)
        merged_payload.update(metadata)

    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        prefix=output_path.stem + "-",
        suffix=".npz",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        np.savez_compressed(temp_path, **merged_payload)
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    for dataset in discover_preprocessed_artifacts(output_dir):
        if dataset.path == output_path:
            return dataset

    raise FileNotFoundError(f"Failed to discover freshly written dataset: {output_path}")


def _load_existing_npz(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with np.load(path, allow_pickle=False) as existing:
        return {key: np.array(existing[key], copy=True) for key in existing.files}


def _merge_trade_payload(
    existing: Mapping[str, object],
    payload: Mapping[str, object],
    metadata: Mapping[str, object],
) -> dict[str, object]:
    latest_value = payload.get("trade_window_seconds_latest")
    if latest_value is None:
        raise PreprocessValidationError(
            "Trade payload is missing trade_window_seconds_latest metadata."
        )
    try:
        trade_window_seconds = int(latest_value)
    except (TypeError, ValueError) as error:
        raise PreprocessValidationError(
            f"Invalid trade_window_seconds_latest metadata: {latest_value!r}"
        ) from error

    suffix = f"__w{trade_window_seconds}"
    window_keys = {
        f"trade_time{suffix}",
        f"trade_price{suffix}",
        f"trade_volume{suffix}",
        f"trade_side{suffix}",
    }
    missing_window_keys = sorted(window_keys - set(payload))
    if missing_window_keys:
        raise PreprocessValidationError(
            "Trade payload is missing required windowed keys: "
            + ", ".join(missing_window_keys)
        )

    merged = dict(existing)
    merged.update(metadata)
    for key in window_keys:
        merged[key] = payload[key]

    existing_windows_raw = existing.get("trade_window_seconds_available")
    existing_windows: set[int] = set()
    if existing_windows_raw is not None:
        existing_windows = {
            int(item) for item in np.asarray(existing_windows_raw, dtype=int).tolist()
        }
    existing_windows.add(trade_window_seconds)
    merged["trade_window_seconds_available"] = np.asarray(
        sorted(existing_windows),
        dtype=int,
    )
    merged["trade_window_seconds_latest"] = int(trade_window_seconds)
    return merged


def _merge_orderbook_payload(
    existing: Mapping[str, object],
    payload: Mapping[str, object],
    metadata: Mapping[str, object],
) -> dict[str, object]:
    latest_value = payload.get("orderbook_window_seconds_latest")
    if latest_value is None:
        raise PreprocessValidationError(
            "Orderbook payload is missing orderbook_window_seconds_latest metadata."
        )
    try:
        trade_window_seconds = int(latest_value)
    except (TypeError, ValueError) as error:
        raise PreprocessValidationError(
            f"Invalid orderbook_window_seconds_latest metadata: {latest_value!r}"
        ) from error

    suffix = f"__w{trade_window_seconds}"
    window_keys = {
        f"time_axis{suffix}",
        f"bid_price{suffix}",
        f"bid_size{suffix}",
        f"ask_price{suffix}",
        f"ask_size{suffix}",
        f"bid{suffix}",
        f"ask{suffix}",
        f"mid{suffix}",
    }
    missing_window_keys = sorted(window_keys - set(payload))
    if missing_window_keys:
        raise PreprocessValidationError(
            "Orderbook payload is missing required windowed keys: "
            + ", ".join(missing_window_keys)
        )

    merged = {
        key: value
        for key, value in existing.items()
        if key not in {
            "time_axis",
            "bid_price",
            "bid_size",
            "ask_price",
            "ask_size",
            "bid",
            "ask",
            "mid",
        }
    }
    merged.update(metadata)
    for key in window_keys:
        merged[key] = payload[key]

    existing_windows_raw = existing.get("orderbook_window_seconds_available")
    existing_windows: set[int] = set()
    if existing_windows_raw is not None:
        existing_windows = {
            int(item) for item in np.asarray(existing_windows_raw, dtype=int).tolist()
        }
    existing_windows.add(trade_window_seconds)
    merged["orderbook_window_seconds_available"] = np.asarray(
        sorted(existing_windows),
        dtype=int,
    )
    merged["orderbook_window_seconds_latest"] = int(trade_window_seconds)
    return merged


def preprocess_batch(
    batch: RawBatch,
    output_dir: Path,
    depth: int = DEFAULT_DEPTH,
    builder_registry: Mapping[str, PreprocessBuilderSpec] | None = None,
    preprocess_timestamp: str | None = None,
    trade_window_seconds: int = 1,
) -> list[PreprocessedDataset]:
    context = build_preprocess_context(
        batch,
        depth,
        trade_window_seconds=trade_window_seconds,
    )
    registry = PLOT_REGISTRY if builder_registry is None else builder_registry
    preprocess_timestamp = preprocess_timestamp or batch.timestamp
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
            )
        )

    return datasets


def preprocess_batches(
    batches: list[RawBatch],
    output_dir: Path,
    depth: int = DEFAULT_DEPTH,
    builder_registry: Mapping[str, PreprocessBuilderSpec] | None = None,
    progress_callback: Callable[[str], None] | None = None,
    preprocess_timestamp: str | None = None,
    trade_window_seconds: int = 1,
) -> list[PreprocessedDataset]:
    results: list[PreprocessedDataset] = []
    total = len(batches)

    for index, batch in enumerate(batches, start=1):
        if progress_callback is not None:
            progress_callback(f"[{index}/{total}] preprocessing {batch.display_name}")
        results.extend(
            preprocess_batch(
                batch,
                output_dir=output_dir,
                depth=depth,
                builder_registry=builder_registry,
                preprocess_timestamp=preprocess_timestamp or batch.timestamp,
                trade_window_seconds=trade_window_seconds,
            )
        )

    if progress_callback is not None and batches:
        progress_callback(f"Finished preprocessing {len(batches)} batch(es).")

    return results

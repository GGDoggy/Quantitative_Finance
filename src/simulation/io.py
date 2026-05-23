from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.dataset_artifacts import build_simulation_output_path
from src.raw_batches import LoadedRawBatch, RawBatch, discover_raw_batches, load_raw_batch

from .models import LoadedMarketData, SimulationResult

SIMULATION_RESULT_KEYS = (
    "bid_prices",
    "bid_near_size",
    "bid_opp_size",
    "bid_survival_time",
    "bid_ahead",
    "bid_behind",
    "bid_vorder_ratio",
    "bid_result",
    "bid_spread",
    "ask_prices",
    "ask_near_size",
    "ask_opp_size",
    "ask_survival_time",
    "ask_ahead",
    "ask_behind",
    "ask_vorder_ratio",
    "ask_result",
    "ask_spread",
    "bid_mid_price",
    "bid_micro_price",
    "bid_mid_profit",
    "bid_micro_profit",
    "ask_mid_price",
    "ask_micro_price",
    "ask_mid_profit",
    "ask_micro_profit",
)

SIMULATION_METADATA_KEYS = (
    "algorithm",
    "product_id",
    "file_stem",
    "time_step",
    "base_tick",
    "resolved_time",
)


def build_output_path(
    output_path: Path | str,
    product_id: str,
    timestamp: str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float,
) -> Path:
    return build_simulation_output_path(
        output_path,
        product_id,
        timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )


def parse_dataset_groups(data_v3_path: Path | str) -> list[RawBatch]:
    return discover_raw_batches(data_v3_path)


def load_raw_dataset(dataset: RawBatch) -> LoadedMarketData:
    loaded_batch: LoadedRawBatch = load_raw_batch(dataset)
    return LoadedMarketData(
        init=loaded_batch.init,
        updates=loaded_batch.updates,
        trades=loaded_batch.trades,
        start_time=loaded_batch.start_time,
    )


def serialize_result_for_npz(result: SimulationResult) -> dict[str, Any]:
    return dict(zip(SIMULATION_RESULT_KEYS, result.as_tuple()))


def save_result_file(
    output_file: Path,
    *,
    algorithm_name: str,
    dataset: RawBatch,
    time_step: float,
    base_tick: float,
    resolved_time: float,
    result: SimulationResult,
) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {
        "algorithm": algorithm_name,
        "product_id": dataset.product_id,
        "file_stem": dataset.file_stem,
        "time_step": time_step,
        "base_tick": base_tick,
        "resolved_time": resolved_time,
    }
    save_kwargs.update(serialize_result_for_npz(result))
    np.savez_compressed(output_file, **save_kwargs)
    return output_file

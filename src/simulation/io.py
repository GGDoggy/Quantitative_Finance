from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ._simulation_core import file_time_to_unix, read_csv
from .constants import DEFAULT_RESOLVED_TIME
from .models import LoadedMarketData, RawSimulationDataset, SimulationResult

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
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> Path:
    filename = (
        f"{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}"
        f"-simulation-{algorithm_name}.npz"
    )
    return Path(output_path) / filename


def parse_dataset_groups(data_v3_path: Path | str) -> list[RawSimulationDataset]:
    grouped: dict[tuple[str, str], dict[str, Path | None]] = {}
    for path in sorted(Path(data_v3_path).glob("*.csv")):
        stem_parts = path.stem.split("-")
        if len(stem_parts) < 4:
            continue

        if stem_parts[0] == "level2" and stem_parts[-2] in {"init", "updates"}:
            data_type = stem_parts[-2]
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-2])
        elif stem_parts[0] == "trade":
            data_type = "trade"
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-1])
        else:
            continue

        key = (product_id, timestamp)
        if key not in grouped:
            grouped[key] = {"init": None, "updates": None, "trade": None}
        grouped[key][data_type] = path

    available: list[RawSimulationDataset] = []
    for (product_id, timestamp), parts in grouped.items():
        init, updates, trade = parts["init"], parts["updates"], parts["trade"]
        if init is None or updates is None or trade is None:
            continue
        available.append(
            RawSimulationDataset(
                product_id=product_id,
                timestamp=timestamp,
                file_stem=f"{product_id}-{timestamp}",
                init=init,
                updates=updates,
                trade=trade,
            )
        )

    return sorted(available, key=lambda item: (item.product_id, item.timestamp))


def load_raw_dataset(dataset: RawSimulationDataset) -> LoadedMarketData:
    init = read_csv(dataset.init)
    updates = read_csv(dataset.updates)
    trades = read_csv(dataset.trade)
    start_time = file_time_to_unix(dataset.timestamp)
    return LoadedMarketData(
        init=init,
        updates=updates,
        trades=trades,
        start_time=start_time,
    )


def serialize_result_for_npz(result: SimulationResult) -> dict[str, Any]:
    return dict(zip(SIMULATION_RESULT_KEYS, result.as_tuple()))


def save_result_file(
    output_file: Path,
    *,
    algorithm_name: str,
    dataset: RawSimulationDataset,
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

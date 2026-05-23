"""Legacy compatibility facade for the pre-refactor simulation API.

Do not add new imports against this module. New code should import from
``src.simulation`` instead.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .constants import DEFAULT_RESOLVED_TIME
from .io import (
    build_output_path,
    load_raw_dataset,
    parse_dataset_groups as parse_raw_dataset_groups,
)
from .models import RawSimulationDataset, SimulationRequest, SimulationResult
from .registry import get_algorithm, list_algorithms
from .runner import (
    run_datasets_in_parallel as run_dataset_jobs_in_parallel,
    save_result,
    simulate_batch,
    simulate_loaded_data,
)

LegacyDataset = Mapping[str, object]


def get_algorithm_names() -> list[str]:
    return list_algorithms()


def _coerce_dataset(dataset: RawSimulationDataset | LegacyDataset) -> RawSimulationDataset:
    if isinstance(dataset, RawSimulationDataset):
        return dataset
    return RawSimulationDataset(
        product_id=str(dataset["product_id"]),
        timestamp=str(dataset["timestamp"]),
        file_stem=str(dataset.get("file_stem", f"{dataset['product_id']}-{dataset['timestamp']}")),
        init_path=Path(dataset.get("init_path", dataset["init"])),
        updates_path=Path(dataset.get("updates_path", dataset["updates"])),
        trade_path=Path(dataset.get("trade_path", dataset["trade"])),
    )


def _legacy_dataset(dataset: RawSimulationDataset) -> dict[str, object]:
    return {
        "product_id": dataset.product_id,
        "timestamp": dataset.timestamp,
        "file_stem": dataset.file_stem,
        "init": dataset.init_path,
        "updates": dataset.updates_path,
        "trade": dataset.trade_path,
    }


def _coerce_result(result: SimulationResult | Sequence[object]) -> SimulationResult:
    if isinstance(result, SimulationResult):
        return result
    return SimulationResult.from_algorithm_output(tuple(result))


def parse_dataset_groups(data_v3_path: Path | str) -> list[dict[str, object]]:
    return [_legacy_dataset(dataset) for dataset in parse_raw_dataset_groups(data_v3_path)]


def is_processed(
    dataset: RawSimulationDataset | LegacyDataset,
    output_path: Path | str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> bool:
    normalized = _coerce_dataset(dataset)
    return build_output_path(
        output_path,
        normalized.product_id,
        normalized.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    ).exists()


def format_dataset_line(
    index: int,
    dataset: RawSimulationDataset | LegacyDataset,
    output_path: Path | str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> str:
    normalized = _coerce_dataset(dataset)
    output_file = build_output_path(
        output_path,
        normalized.product_id,
        normalized.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return f"[{index}] {normalized.file_stem} -> {output_file.name}"


def parse_selection(selection: str, item_count: int) -> list[int]:
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(item_count))

    chosen = []
    for token in selection.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"Invalid selection token: {token}")
        index = int(token) - 1
        if index < 0 or index >= item_count:
            raise ValueError(f"Selection out of range: {token}")
        chosen.append(index)

    if not chosen:
        raise ValueError("No dataset selected.")
    return sorted(set(chosen))


def run_dataset_simulation(
    dataset: RawSimulationDataset | LegacyDataset,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> tuple[Any, ...]:
    normalized = _coerce_dataset(dataset)
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    result = simulate_loaded_data(load_raw_dataset(normalized), request)
    return result.as_tuple()


def save_simulation_npz(
    dataset: RawSimulationDataset | LegacyDataset,
    output_path: Path | str,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    result: SimulationResult | Sequence[object],
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> Path:
    normalized = _coerce_dataset(dataset)
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    return save_result(_coerce_result(result), normalized, request, output_path)


def run_datasets_in_parallel(
    selected: list[RawSimulationDataset | LegacyDataset],
    output_path: Path | str,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> list[dict[str, object]]:
    datasets = [_coerce_dataset(dataset) for dataset in selected]
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    results = run_dataset_jobs_in_parallel(datasets, output_path, request)
    return [
        {
            "file_stem": result.file_stem,
            "output_file": result.output_file,
            "overwritten": result.overwritten,
        }
        for result in results
    ]

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
from typing import Any

import numpy as np

from src.dataset_artifacts import build_simulation_output_path
from src.raw_batches import LoadedRawBatch, RawBatch, discover_raw_batches, load_raw_batch

from .algorithms import get_algorithm, list_algorithms
from .models import (
    LoadedMarketData,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
    SimulationWorkerPayload,
)


DATA_V3_PATH = Path("data/v3")
OUTPUT_PATH = Path("data/preprocessed")
DEFAULT_TIME_STEP = 0.01
DEFAULT_BASE_TICK = 0.00000001
DEFAULT_RESOLVED_TIME = 1.0
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
    depth: int,
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
        "depth": depth,
    }
    save_kwargs.update(serialize_result_for_npz(result))
    np.savez_compressed(output_file, **save_kwargs)
    return output_file


def _run_simulation(
    request: SimulationRequest,
    loaded_data: LoadedMarketData,
) -> SimulationResult:
    algorithm = get_algorithm(request.algorithm)
    return SimulationResult.from_algorithm_output(
        algorithm(
            loaded_data.init,
            loaded_data.updates,
            loaded_data.trades,
            loaded_data.start_time,
            time_step=request.time_step,
            base_tick=request.base_tick,
            resolved_time=request.resolved_time,
            depth=request.depth,
        )
    )


def _save_result(
    result: SimulationResult,
    dataset: RawBatch,
    request: SimulationRequest,
    output_dir: Path | str,
) -> Path:
    output_file = build_output_path(
        output_dir,
        dataset.product_id,
        dataset.timestamp,
        request.time_step,
        request.algorithm,
        request.resolved_time,
    )
    return save_result_file(
        output_file,
        algorithm_name=request.algorithm,
        dataset=dataset,
        time_step=request.time_step,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
        depth=request.depth,
        result=result,
    )


def simulate_loaded_data(
    data: LoadedMarketData,
    request: SimulationRequest,
) -> SimulationResult:
    return _run_simulation(request, data)


def simulate_batch(
    dataset: RawBatch,
    request: SimulationRequest,
    output_dir: Path | str,
) -> SimulationJobResult:
    output_path = build_output_path(
        output_dir,
        dataset.product_id,
        dataset.timestamp,
        request.time_step,
        request.algorithm,
        request.resolved_time,
    )
    overwritten = output_path.exists()
    loaded_data = load_raw_dataset(dataset)
    result = simulate_loaded_data(loaded_data, request)
    saved_path = _save_result(result, dataset, request, output_dir)
    return SimulationJobResult(
        dataset=dataset,
        output_path=saved_path,
        overwritten=overwritten,
    )


def get_default_worker_count(task_count: int) -> int:
    detected = os.cpu_count() or 1
    return max(1, min(task_count, detected))


def _process_dataset_job(
    dataset: RawBatch,
    output_path: Path | str,
    request: SimulationRequest,
) -> SimulationWorkerPayload:
    output_file = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        request.time_step,
        request.algorithm,
        request.resolved_time,
    )
    overwritten = output_file.exists()
    loaded_data = load_raw_dataset(dataset)
    result = simulate_loaded_data(loaded_data, request)
    saved_path = _save_result(result, dataset, request, output_path)
    return SimulationWorkerPayload(
        file_stem=dataset.file_stem,
        output_file=str(saved_path),
        overwritten=overwritten,
    )


def _run_datasets_in_parallel(
    selected: list[RawBatch],
    output_path: Path | str,
    request: SimulationRequest,
) -> list[SimulationWorkerPayload]:
    worker_count = get_default_worker_count(len(selected))
    results: list[SimulationWorkerPayload] = []
    failures: list[tuple[str, Exception]] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(_process_dataset_job, dataset, output_path, request): dataset
            for dataset in selected
        }
        for future in as_completed(future_to_dataset):
            dataset = future_to_dataset[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append((dataset.file_stem, exc))

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        raise RuntimeError(f"Batch processing failed for: {failed_stems}")

    return results


def simulate_batches(
    datasets: list[RawBatch],
    request: SimulationRequest,
    output_dir: Path | str,
) -> list[SimulationJobResult]:
    if len(datasets) <= 1:
        return [simulate_batch(dataset, request, output_dir) for dataset in datasets]

    results = _run_datasets_in_parallel(datasets, output_dir, request)
    dataset_by_stem = {dataset.file_stem: dataset for dataset in datasets}
    job_results = [
        result.to_job_result(dataset_by_stem[result.file_stem])
        for result in results
    ]
    order_by_stem = {dataset.file_stem: index for index, dataset in enumerate(datasets)}
    job_results.sort(key=lambda result: order_by_stem[result.dataset.file_stem])
    return job_results

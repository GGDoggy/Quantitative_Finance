from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import fields
from datetime import datetime
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
    "bid_depth",
    "bid_near_size",
    "bid_opp_size",
    "bid_survival_time",
    "bid_ahead",
    "bid_behind",
    "bid_vorder_ratio",
    "bid_result",
    "bid_spread",
    "ask_prices",
    "ask_depth",
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
SIMULATION_TIMEZONE = ZoneInfo("Asia/Taipei")


def generate_simulation_timestamp() -> str:
    now = datetime.now(SIMULATION_TIMEZONE)
    return f"{now.strftime('%Y%m%d.%H%M%S')}.{now.microsecond // 1000:03d}"


def build_output_path(
    output_path: Path | str,
    algorithm_name: str,
    simulation_timestamp: str,
    seq_num: int,
) -> Path:
    return build_simulation_output_path(
        output_path,
        algorithm_name,
        simulation_timestamp,
        seq_num,
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


def _simulation_result_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in fields(SimulationResult))


def merge_simulation_results(results_by_depth: list[SimulationResult]) -> SimulationResult:
    if not results_by_depth:
        raise ValueError("At least one simulation result is required to merge.")

    merged_payload: dict[str, np.ndarray] = {}
    for field_name in _simulation_result_field_names():
        merged_payload[field_name] = np.concatenate(
            [np.asarray(getattr(result, field_name)) for result in results_by_depth]
        )
    return SimulationResult(**merged_payload)


def simulate_single_depth_loaded_data(
    data: LoadedMarketData,
    request: SimulationRequest,
    depth: int,
) -> SimulationResult:
    single_depth_request = SimulationRequest(
        algorithm=request.algorithm,
        time_step=request.time_step,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
        depths=[depth],
    )
    return _run_simulation(single_depth_request, data)


def save_result_file(
    output_file: Path,
    *,
    algorithm_name: str,
    simulation_timestamp: str,
    seq_num: int,
    dataset: RawBatch,
    time_step: float,
    base_tick: float,
    resolved_time: float,
    depths: list[int],
    result: SimulationResult,
) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {
        "algorithm": algorithm_name,
        "simulation_timestamp": simulation_timestamp,
        "seq_num": int(seq_num),
        "product_id": dataset.product_id,
        "timestamp": dataset.timestamp,
        "file_stem": dataset.file_stem,
        "time_step": time_step,
        "base_tick": base_tick,
        "resolved_time": resolved_time,
        "depths": np.asarray(depths, dtype=int),
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
            depths=request.depths,
        )
    )


def simulate_loaded_data(
    data: LoadedMarketData,
    request: SimulationRequest,
) -> SimulationResult:
    if len(request.depths) == 1:
        return _run_simulation(request, data)

    results_by_depth = [
        simulate_single_depth_loaded_data(data, request, depth)
        for depth in request.depths
    ]
    return merge_simulation_results(results_by_depth)


def simulate_batch(
    dataset: RawBatch,
    request: SimulationRequest,
    output_dir: Path | str,
) -> SimulationJobResult:
    simulation_timestamp = generate_simulation_timestamp()
    seq_num = 0
    output_path = build_output_path(
        output_dir,
        request.algorithm,
        simulation_timestamp,
        seq_num,
    )
    overwritten = output_path.exists()
    loaded_data = load_raw_dataset(dataset)
    result = simulate_loaded_data(loaded_data, request)
    saved_path = save_result_file(
        output_path,
        algorithm_name=request.algorithm,
        simulation_timestamp=simulation_timestamp,
        seq_num=seq_num,
        dataset=dataset,
        time_step=request.time_step,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
        depths=request.depths,
        result=result,
    )
    return SimulationJobResult(
        dataset=dataset,
        output_path=saved_path,
        overwritten=overwritten,
        seq_num=seq_num,
    )


def get_default_worker_count(task_count: int) -> int:
    detected = os.cpu_count() or 1
    return max(1, min(task_count, detected))


def _process_dataset_job(
    dataset: RawBatch,
    output_path: Path | str,
    request: SimulationRequest,
    simulation_timestamp: str,
    seq_num: int,
) -> SimulationWorkerPayload:
    output_file = build_output_path(
        output_path,
        request.algorithm,
        simulation_timestamp,
        seq_num,
    )
    overwritten = output_file.exists()
    loaded_data = load_raw_dataset(dataset)
    result = simulate_loaded_data(loaded_data, request)
    saved_path = save_result_file(
        output_file,
        algorithm_name=request.algorithm,
        simulation_timestamp=simulation_timestamp,
        seq_num=seq_num,
        dataset=dataset,
        time_step=request.time_step,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
        depths=request.depths,
        result=result,
    )
    return SimulationWorkerPayload(
        file_stem=dataset.file_stem,
        output_file=str(saved_path),
        overwritten=overwritten,
        seq_num=seq_num,
    )


def _run_datasets_in_parallel(
    selected: list[RawBatch],
    output_path: Path | str,
    request: SimulationRequest,
) -> list[SimulationWorkerPayload]:
    worker_count = get_default_worker_count(len(selected))
    simulation_timestamp = generate_simulation_timestamp()
    results: list[SimulationWorkerPayload] = []
    failures: list[tuple[str, Exception]] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(
                _process_dataset_job,
                dataset,
                output_path,
                request,
                simulation_timestamp,
                seq_num,
            ): dataset
            for seq_num, dataset in enumerate(selected)
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

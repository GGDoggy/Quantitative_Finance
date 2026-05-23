from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path

from .io import build_output_path, load_raw_dataset, save_result_file
from .models import (
    LoadedMarketData,
    RawSimulationDataset,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
    SimulationWorkerPayload,
)
from .registry import get_algorithm


def run_simulation_request(
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
        )
    )


def save_result(
    result: SimulationResult,
    dataset: RawSimulationDataset,
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
        result=result,
    )


def simulate_loaded_data(
    data: LoadedMarketData,
    request: SimulationRequest,
) -> SimulationResult:
    return run_simulation_request(request, data)


def simulate_batch(
    dataset: RawSimulationDataset,
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
    saved_path = save_result(result, dataset, request, output_dir)
    return SimulationJobResult(
        dataset=dataset,
        output_path=saved_path,
        overwritten=overwritten,
    )


def get_default_worker_count(task_count: int) -> int:
    detected = os.cpu_count() or 1
    return max(1, min(task_count, detected))


def process_dataset_job(
    dataset: RawSimulationDataset,
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
    saved_path = save_result(result, dataset, request, output_path)
    return SimulationWorkerPayload(
        file_stem=dataset.file_stem,
        output_file=str(saved_path),
        overwritten=overwritten,
    )


def run_datasets_in_parallel(
    selected: list[RawSimulationDataset],
    output_path: Path | str,
    request: SimulationRequest,
) -> list[SimulationWorkerPayload]:
    worker_count = get_default_worker_count(len(selected))
    results: list[SimulationWorkerPayload] = []
    failures: list[tuple[str, Exception]] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(process_dataset_job, dataset, output_path, request): dataset
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
    datasets: list[RawSimulationDataset],
    request: SimulationRequest,
    output_dir: Path | str,
) -> list[SimulationJobResult]:
    if len(datasets) <= 1:
        return [simulate_batch(dataset, request, output_dir) for dataset in datasets]

    results = run_datasets_in_parallel(datasets, output_dir, request)
    dataset_by_stem = {dataset.file_stem: dataset for dataset in datasets}
    job_results = [
        result.to_job_result(dataset_by_stem[result.file_stem])
        for result in results
    ]
    order_by_stem = {dataset.file_stem: index for index, dataset in enumerate(datasets)}
    job_results.sort(key=lambda result: order_by_stem[result.dataset.file_stem])
    return job_results

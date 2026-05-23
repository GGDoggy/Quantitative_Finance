"""UI-friendly helpers for running fill-probability simulations from raw batches."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .constants import DEFAULT_BASE_TICK, DEFAULT_RESOLVED_TIME
from .io import build_output_path, load_raw_dataset, save_result_file
from .models import (
    LoadedMarketData,
    RawSimulationDataset,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
)
from .registry import get_algorithm, list_algorithms as list_registered_algorithms
from .runner import run_datasets_in_parallel, run_simulation_request

if TYPE_CHECKING:
    from src.preprocess.catalog import RawBatch


def _to_simulation_dataset(raw_batch: RawBatch) -> RawSimulationDataset:
    return RawSimulationDataset(
        product_id=raw_batch.product_id,
        timestamp=raw_batch.timestamp,
        file_stem=f"{raw_batch.product_id}-{raw_batch.timestamp}",
        init_path=raw_batch.init_path,
        updates_path=raw_batch.updates_path,
        trade_path=raw_batch.trade_path,
    )


def _validate_request(request: SimulationRequest) -> None:
    get_algorithm(request.algorithm)


def _saved_action_message(simulation_result: SimulationJobResult) -> str:
    action = "overwrote" if simulation_result.overwritten else "saved"
    return f"{action} {simulation_result.output_path.name}"


def list_algorithms() -> list[str]:
    """Return the registered simulation algorithm names."""
    return list_registered_algorithms()


def simulate_loaded_data(
    loaded_data: LoadedMarketData,
    *,
    algorithm_name: str,
    time_step: float,
    base_tick: float = DEFAULT_BASE_TICK,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> SimulationResult:
    """Simulate from pre-loaded market arrays without re-reading CSV files."""
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    _validate_request(request)
    return run_simulation_request(request, loaded_data)


def save_result(
    dataset: RawSimulationDataset,
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    result: SimulationResult,
    base_tick: float = DEFAULT_BASE_TICK,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> Path:
    """Save one simulation result to npz using standard naming convention."""
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    _validate_request(request)
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


def simulate_batch(
    raw_batch: RawBatch,
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
    base_tick: float = DEFAULT_BASE_TICK,
) -> SimulationJobResult:
    dataset = _to_simulation_dataset(raw_batch)
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    _validate_request(request)
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
    result = run_simulation_request(request, loaded_data)
    saved_path = save_result(
        dataset,
        output_dir=output_dir,
        algorithm_name=request.algorithm,
        time_step=request.time_step,
        result=result,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
    )
    return SimulationJobResult(
        dataset=dataset,
        output_path=saved_path,
        overwritten=overwritten,
    )


def simulate_batches(
    raw_batches: list[RawBatch],
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
    base_tick: float = DEFAULT_BASE_TICK,
    progress_callback: Callable[[str], None] | None = None,
) -> list[SimulationJobResult]:
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    _validate_request(request)
    total = len(raw_batches)
    if total <= 1:
        results: list[SimulationJobResult] = []
        for index, raw_batch in enumerate(raw_batches, start=1):
            if progress_callback is not None:
                progress_callback(f"[{index}/{total}] simulating {raw_batch.display_name}")

            simulation_result = simulate_batch(
                raw_batch,
                output_dir=output_dir,
                algorithm_name=request.algorithm,
                time_step=request.time_step,
                resolved_time=request.resolved_time,
                base_tick=request.base_tick,
            )
            if progress_callback is not None:
                progress_callback(_saved_action_message(simulation_result))
            results.append(simulation_result)

        if progress_callback is not None and raw_batches:
            progress_callback(f"Finished simulation for {len(raw_batches)} batch(es).")
        return results

    dataset_by_stem = {
        f"{raw_batch.product_id}-{raw_batch.timestamp}": _to_simulation_dataset(raw_batch)
        for raw_batch in raw_batches
    }
    raw_batch_order = {
        f"{raw_batch.product_id}-{raw_batch.timestamp}": index
        for index, raw_batch in enumerate(raw_batches)
    }
    datasets = [_to_simulation_dataset(raw_batch) for raw_batch in raw_batches]
    job_results = run_datasets_in_parallel(
        datasets,
        output_dir,
        request,
    )
    results = [
        job_result.to_job_result(dataset_by_stem[job_result.file_stem])
        for job_result in job_results
    ]
    results.sort(
        key=lambda simulation_result: raw_batch_order[
            f"{simulation_result.dataset.product_id}-"
            f"{simulation_result.dataset.timestamp}"
        ]
    )
    if progress_callback is not None:
        for simulation_result in results:
            progress_callback(_saved_action_message(simulation_result))
        progress_callback(f"Finished simulation for {len(raw_batches)} batch(es).")
    return results

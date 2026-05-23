"""GUI-facing adapters that bridge RawBatch objects to the simulation library."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .constants import DEFAULT_BASE_TICK, DEFAULT_RESOLVED_TIME
from .models import RawSimulationDataset, SimulationJobResult, SimulationRequest
from .registry import get_algorithm, list_algorithms as list_registered_algorithms
from .runner import simulate_batch as simulate_dataset_batch
from .runner import simulate_batches as simulate_dataset_batches

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


def _build_request(
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float,
) -> SimulationRequest:
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    get_algorithm(request.algorithm)
    return request


def _saved_action_message(simulation_result: SimulationJobResult) -> str:
    action = "overwrote" if simulation_result.overwritten else "saved"
    return f"{action} {simulation_result.output_path.name}"


def list_algorithms() -> list[str]:
    """Return the registered simulation algorithm names."""
    return list_registered_algorithms()


def simulate_raw_batch(
    raw_batch: RawBatch,
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
    base_tick: float = DEFAULT_BASE_TICK,
) -> SimulationJobResult:
    dataset = _to_simulation_dataset(raw_batch)
    request = _build_request(
        algorithm_name,
        time_step,
        base_tick,
        resolved_time,
    )
    return simulate_dataset_batch(dataset, request, output_dir)


def simulate_raw_batches(
    raw_batches: list[RawBatch],
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
    base_tick: float = DEFAULT_BASE_TICK,
    progress_callback: Callable[[str], None] | None = None,
) -> list[SimulationJobResult]:
    request = _build_request(
        algorithm_name,
        time_step,
        base_tick,
        resolved_time,
    )
    total = len(raw_batches)
    if total <= 1:
        results: list[SimulationJobResult] = []
        for index, raw_batch in enumerate(raw_batches, start=1):
            if progress_callback is not None:
                progress_callback(f"[{index}/{total}] simulating {raw_batch.display_name}")

            simulation_result = simulate_raw_batch(
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

    raw_batch_order = {
        f"{raw_batch.product_id}-{raw_batch.timestamp}": index
        for index, raw_batch in enumerate(raw_batches)
    }
    datasets = [_to_simulation_dataset(raw_batch) for raw_batch in raw_batches]
    results = simulate_dataset_batches(datasets, request, output_dir)
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

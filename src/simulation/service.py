"""UI-friendly helpers for running fill-probability simulations from raw batches."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
from typing import TYPE_CHECKING, Callable

from .constants import DEFAULT_RESOLVED_TIME
from .library import (
    DEFAULT_BASE_TICK,
    build_output_path,
    get_algorithm,
    run_datasets_in_parallel,
    run_dataset_simulation,
    save_simulation_npz,
)

if TYPE_CHECKING:
    from src.preprocess import RawBatch


@dataclass(frozen=True)
class SimulationJobResult:
    raw_batch: RawBatch
    output_path: Path
    overwritten: bool


def _validate_parameters(
    algorithm_name: str,
    time_step: float,
    resolved_time: float,
) -> None:
    get_algorithm(algorithm_name)
    if not math.isfinite(time_step):
        raise ValueError("Simulation time_step must be finite.")
    if time_step <= 0:
        raise ValueError("Simulation time_step must be positive.")
    if not math.isfinite(resolved_time):
        raise ValueError("Simulation resolved_time must be finite.")
    if resolved_time < 0:
        raise ValueError("Simulation resolved_time must be non-negative.")


def _to_simulation_dataset(raw_batch: RawBatch) -> dict[str, object]:
    return {
        "product_id": raw_batch.product_id,
        "timestamp": raw_batch.timestamp,
        "file_stem": f"{raw_batch.product_id}-{raw_batch.timestamp}",
        "init": raw_batch.init_path,
        "updates": raw_batch.updates_path,
        "trade": raw_batch.trade_path,
    }


def _saved_action_message(simulation_result: SimulationJobResult) -> str:
    action = "overwrote" if simulation_result.overwritten else "saved"
    return f"{action} {simulation_result.output_path.name}"


def simulate_batch(
    raw_batch: RawBatch,
    *,
    output_dir: Path,
    algorithm_name: str,
    time_step: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
    base_tick: float = DEFAULT_BASE_TICK,
) -> SimulationJobResult:
    _validate_parameters(algorithm_name, time_step, resolved_time)
    dataset = _to_simulation_dataset(raw_batch)
    output_path = build_output_path(
        output_dir,
        dataset["product_id"],
        dataset["timestamp"],
        time_step,
        algorithm_name,
        resolved_time,
    )
    overwritten = output_path.exists()
    result = run_dataset_simulation(
        dataset,
        algorithm_name,
        time_step,
        base_tick,
        resolved_time,
    )
    saved_path = save_simulation_npz(
        dataset,
        output_dir,
        algorithm_name,
        time_step,
        base_tick,
        result,
        resolved_time,
    )
    return SimulationJobResult(
        raw_batch=raw_batch,
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
    _validate_parameters(algorithm_name, time_step, resolved_time)
    total = len(raw_batches)
    if total <= 1:
        results: list[SimulationJobResult] = []
        for index, raw_batch in enumerate(raw_batches, start=1):
            if progress_callback is not None:
                progress_callback(f"[{index}/{total}] simulating {raw_batch.display_name}")

            simulation_result = simulate_batch(
                raw_batch,
                output_dir=output_dir,
                algorithm_name=algorithm_name,
                time_step=time_step,
                resolved_time=resolved_time,
                base_tick=base_tick,
            )
            if progress_callback is not None:
                progress_callback(_saved_action_message(simulation_result))
            results.append(simulation_result)

        if progress_callback is not None and raw_batches:
            progress_callback(f"Finished simulation for {len(raw_batches)} batch(es).")
        return results

    raw_batch_by_stem = {
        f"{raw_batch.product_id}-{raw_batch.timestamp}": raw_batch
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
        algorithm_name,
        time_step,
        base_tick,
        resolved_time,
    )
    results = [
        SimulationJobResult(
            raw_batch=raw_batch_by_stem[job_result["file_stem"]],
            output_path=Path(job_result["output_file"]),
            overwritten=bool(job_result["overwritten"]),
        )
        for job_result in job_results
    ]
    results.sort(
        key=lambda simulation_result: raw_batch_order[
            f"{simulation_result.raw_batch.product_id}-"
            f"{simulation_result.raw_batch.timestamp}"
        ]
    )
    if progress_callback is not None:
        for simulation_result in results:
            progress_callback(_saved_action_message(simulation_result))
        progress_callback(f"Finished simulation for {len(raw_batches)} batch(es).")
    return results

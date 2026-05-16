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
    run_dataset_simulation,
    save_simulation_npz,
)

if TYPE_CHECKING:
    from src.preprocess.catalog import RawBatch


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
    results: list[SimulationJobResult] = []
    total = len(raw_batches)

    for index, raw_batch in enumerate(raw_batches, start=1):
        if progress_callback is not None:
            progress_callback(f"[{index}/{total}] simulating {raw_batch.display_name}")

        dataset = _to_simulation_dataset(raw_batch)
        output_path = build_output_path(
            output_dir,
            dataset["product_id"],
            dataset["timestamp"],
            time_step,
            algorithm_name,
            resolved_time,
        )
        output_will_be_overwritten = output_path.exists()
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
        action = "overwrote" if output_will_be_overwritten else "saved"
        if progress_callback is not None:
            progress_callback(f"{action} {saved_path.name}")
        results.append(
            SimulationJobResult(
                raw_batch=raw_batch,
                output_path=saved_path,
                overwritten=output_will_be_overwritten,
            )
        )

    if progress_callback is not None and raw_batches:
        progress_callback(f"Finished simulation for {len(raw_batches)} batch(es).")

    return results

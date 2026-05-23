"""Transitional facade that preserves the legacy import surface.

Do not add new imports against this module. New code should import from
``src.simulation`` instead.
"""
from __future__ import annotations

from .compat import (
    build_output_path,
    format_dataset_line,
    get_algorithm,
    get_algorithm_names,
    is_processed,
    parse_dataset_groups,
    parse_selection,
    run_dataset_simulation,
    run_datasets_in_parallel,
    save_simulation_npz,
)
from .constants import (
    DATA_V3_PATH,
    DEFAULT_BASE_TICK,
    DEFAULT_RESOLVED_TIME,
    DEFAULT_TIME_STEP,
    OUTPUT_PATH,
)
from .io import load_raw_dataset
from .models import (
    LoadedMarketData,
    RawSimulationDataset,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
)
from .runner import simulate_batch, simulate_batches, simulate_loaded_data

__all__ = [
    "build_output_path",
    "format_dataset_line",
    "get_algorithm",
    "get_algorithm_names",
    "is_processed",
    "parse_dataset_groups",
    "parse_selection",
    "run_dataset_simulation",
    "run_datasets_in_parallel",
    "save_simulation_npz",
    "simulate_loaded_data",
    "simulate_batch",
    "simulate_batches",
    "load_raw_dataset",
    "LoadedMarketData",
    "RawSimulationDataset",
    "SimulationJobResult",
    "SimulationRequest",
    "SimulationResult",
    "DATA_V3_PATH",
    "DEFAULT_BASE_TICK",
    "DEFAULT_RESOLVED_TIME",
    "DEFAULT_TIME_STEP",
    "OUTPUT_PATH",
]

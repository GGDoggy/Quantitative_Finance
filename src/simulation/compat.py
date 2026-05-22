"""Backward-compatible simulation helpers.

This module preserves legacy function-level APIs while the project migrates to the
new public API exposed from ``src.simulation``.

Deprecation policy:
- Legacy helpers in this module are scheduled for removal in v0.8.0
  (or after 2026-12-31, whichever comes first).
- Callers should migrate to: ``list_algorithms``, ``simulate_loaded_data``,
  ``simulate_batch``, ``simulate_batches``, and ``save_result``.
"""
from __future__ import annotations

import warnings
from dataclasses import asdict
from pathlib import Path

from .constants import DEFAULT_RESOLVED_TIME
from .io import load_raw_dataset as _load_raw_dataset, parse_dataset_groups as _parse_dataset_groups
from .models import RawSimulationDataset, SimulationRequest
from .runner import run_dataset_simulation as _run_dataset_simulation
from .library import (
    build_output_path as _build_output_path,
    format_dataset_line as _format_dataset_line,
    get_algorithm as _get_algorithm,
    get_algorithm_names as _get_algorithm_names,
    is_processed as _is_processed,
    parse_selection as _parse_selection,
    process_dataset_job as _process_dataset_job,
    run_datasets_in_parallel as _run_datasets_in_parallel,
    save_simulation_npz as _save_simulation_npz,
)

_DEPRECATION_NOTE = "Use the new public API exported by src.simulation instead."


def _warn(name: str) -> None:
    warnings.warn(
        f"src.simulation.compat.{name} is deprecated. {_DEPRECATION_NOTE}",
        DeprecationWarning,
        stacklevel=2,
    )


def get_algorithm_names():
    _warn("get_algorithm_names")
    return _get_algorithm_names()


def get_algorithm(name):
    _warn("get_algorithm")
    return _get_algorithm(name)


def parse_dataset_groups(data_v3_path):
    _warn("parse_dataset_groups")
    return [asdict(d) for d in _parse_dataset_groups(data_v3_path)]


def build_output_path(output_path, product_id, timestamp, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("build_output_path")
    return _build_output_path(output_path, product_id, timestamp, time_step, algorithm_name, resolved_time)


def is_processed(dataset, output_path, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("is_processed")
    return _is_processed(dataset, output_path, time_step, algorithm_name, resolved_time)


def load_dataset(dataset):
    _warn("load_dataset")
    return _load_raw_dataset(_to_dataset(dataset))


def run_dataset_simulation(dataset, algorithm_name, time_step, base_tick, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("run_dataset_simulation")
    typed = _to_dataset(dataset)
    req = SimulationRequest(typed, algorithm_name, time_step, base_tick, resolved_time)
    return _run_dataset_simulation(req, _load_raw_dataset(typed))


def save_simulation_npz(dataset, output_path, algorithm_name, time_step, base_tick, result, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("save_simulation_npz")
    return _save_simulation_npz(dataset, output_path, algorithm_name, time_step, base_tick, result, resolved_time)


def format_dataset_line(index, dataset, output_path, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("format_dataset_line")
    return _format_dataset_line(index, dataset, output_path, time_step, algorithm_name, resolved_time)


def parse_selection(selection, item_count):
    _warn("parse_selection")
    return _parse_selection(selection, item_count)


def process_dataset_job(dataset, output_path, algorithm_name, time_step, base_tick, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("process_dataset_job")
    return _process_dataset_job(dataset, output_path, algorithm_name, time_step, base_tick, resolved_time)


def run_datasets_in_parallel(selected, output_path, algorithm_name, time_step, base_tick, resolved_time=DEFAULT_RESOLVED_TIME):
    _warn("run_datasets_in_parallel")
    return _run_datasets_in_parallel(selected, output_path, algorithm_name, time_step, base_tick, resolved_time)


def _to_dataset(dataset):
    if isinstance(dataset, RawSimulationDataset):
        return dataset
    return RawSimulationDataset(**dataset)

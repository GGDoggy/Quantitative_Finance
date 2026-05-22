"""Shared data models for simulation services and helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import numpy as np

if TYPE_CHECKING:
    from src.preprocess.catalog import RawBatch


class RawSimulationDataset(TypedDict):
    """Typed mapping for a single raw simulation dataset."""

    product_id: str
    timestamp: str
    file_stem: str
    init: Path
    updates: Path
    trade: Path


LoadedMarketData = tuple[np.ndarray, np.ndarray, np.ndarray, float]
SimulationResult = tuple[np.ndarray, ...]


@dataclass(frozen=True)
class SimulationRequest:
    dataset: RawSimulationDataset
    algorithm_name: str
    time_step: float
    base_tick: float
    resolved_time: float


@dataclass(frozen=True)
class SimulationJobResult:
    raw_batch: RawBatch
    output_path: Path
    overwritten: bool

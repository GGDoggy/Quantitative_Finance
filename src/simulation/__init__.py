"""Minimal public API for simulation library consumers."""
from .io import load_raw_dataset
from .models import (
    LoadedMarketData,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
)
from .registry import list_algorithms
from .runner import simulate_batch, simulate_batches, simulate_loaded_data
from src.raw_batches import RawBatch

__all__ = [
    "list_algorithms",
    "load_raw_dataset",
    "simulate_loaded_data",
    "simulate_batch",
    "simulate_batches",
    "LoadedMarketData",
    "RawBatch",
    "SimulationJobResult",
    "SimulationRequest",
    "SimulationResult",
]

"""Core data models for the simulation library."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np

from src.raw_batches import RawBatch


@dataclass(frozen=True)
class LoadedMarketData:
    init: list[list[float]]
    updates: list[list[float]]
    trades: list[list[float]]
    start_time: float


@dataclass(frozen=True)
class SimulationResult:
    bid_prices: np.ndarray
    bid_near_size: np.ndarray
    bid_opp_size: np.ndarray
    bid_survival_time: np.ndarray
    bid_ahead: np.ndarray
    bid_behind: np.ndarray
    bid_vorder_ratio: np.ndarray
    bid_result: np.ndarray
    bid_spread: np.ndarray
    ask_prices: np.ndarray
    ask_near_size: np.ndarray
    ask_opp_size: np.ndarray
    ask_survival_time: np.ndarray
    ask_ahead: np.ndarray
    ask_behind: np.ndarray
    ask_vorder_ratio: np.ndarray
    ask_result: np.ndarray
    ask_spread: np.ndarray
    bid_mid_price: np.ndarray
    bid_micro_price: np.ndarray
    bid_mid_profit: np.ndarray
    bid_micro_profit: np.ndarray
    ask_mid_price: np.ndarray
    ask_micro_price: np.ndarray
    ask_mid_profit: np.ndarray
    ask_micro_profit: np.ndarray

    @classmethod
    def from_algorithm_output(cls, values: tuple[np.ndarray, ...]) -> "SimulationResult":
        return cls(*values)

    def as_tuple(self) -> tuple[np.ndarray, ...]:
        return (
            self.bid_prices,
            self.bid_near_size,
            self.bid_opp_size,
            self.bid_survival_time,
            self.bid_ahead,
            self.bid_behind,
            self.bid_vorder_ratio,
            self.bid_result,
            self.bid_spread,
            self.ask_prices,
            self.ask_near_size,
            self.ask_opp_size,
            self.ask_survival_time,
            self.ask_ahead,
            self.ask_behind,
            self.ask_vorder_ratio,
            self.ask_result,
            self.ask_spread,
            self.bid_mid_price,
            self.bid_micro_price,
            self.bid_mid_profit,
            self.bid_micro_profit,
            self.ask_mid_price,
            self.ask_micro_price,
            self.ask_mid_profit,
            self.ask_micro_profit,
        )


@dataclass(frozen=True)
class SimulationRequest:
    algorithm: str
    time_step: float
    base_tick: float
    resolved_time: float
    depth: int = 0

    def __post_init__(self) -> None:
        if not self.algorithm:
            raise ValueError("Simulation algorithm is required.")
        if not math.isfinite(self.time_step) or self.time_step <= 0:
            raise ValueError("Simulation time_step must be a positive finite value.")
        if not math.isfinite(self.base_tick) or self.base_tick <= 0:
            raise ValueError("Simulation base_tick must be a positive finite value.")
        if not math.isfinite(self.resolved_time) or self.resolved_time < 0:
            raise ValueError("Simulation resolved_time must be a non-negative finite value.")
        if not isinstance(self.depth, int) or self.depth < 0:
            raise ValueError("Simulation depth must be a non-negative integer.")


@dataclass(frozen=True)
class SimulationJobResult:
    dataset: RawBatch
    output_path: Path
    overwritten: bool


@dataclass(frozen=True)
class SimulationWorkerPayload:
    file_stem: str
    output_file: str
    overwritten: bool

    def to_job_result(self, dataset: RawBatch) -> SimulationJobResult:
        return SimulationJobResult(
            dataset=dataset,
            output_path=Path(self.output_file),
            overwritten=self.overwritten,
        )

"""Data models for trade fill-rate analysis artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.raw_batches import RawBatch


@dataclass(frozen=True)
class LoadedAnalyzeData:
    init: list[list[float]]
    updates: list[list[float]]
    trades: list[list[float]]
    start_time: float


@dataclass(frozen=True)
class AnalyzeRequest:
    analysis_name: str = "fill_rate"

    def __post_init__(self) -> None:
        if not self.analysis_name:
            raise ValueError("Analyze analysis_name is required.")


@dataclass(frozen=True)
class AnalyzeResult:
    price: np.ndarray
    vol: np.ndarray
    time: np.ndarray
    side: np.ndarray
    penetrated: np.ndarray
    spread: np.ndarray
    opp_vol: np.ndarray
    fill_rate: np.ndarray

    def as_tuple(self) -> tuple[np.ndarray, ...]:
        return (
            self.price,
            self.vol,
            self.time,
            self.side,
            self.penetrated,
            self.spread,
            self.opp_vol,
            self.fill_rate,
        )


@dataclass(frozen=True)
class AnalyzeJobResult:
    dataset: RawBatch
    output_path: Path
    overwritten: bool
    seq_num: int


@dataclass(frozen=True)
class AnalyzeWorkerPayload:
    file_stem: str
    output_file: str
    overwritten: bool
    seq_num: int

    def to_job_result(self, dataset: RawBatch) -> AnalyzeJobResult:
        return AnalyzeJobResult(
            dataset=dataset,
            output_path=Path(self.output_file),
            overwritten=self.overwritten,
            seq_num=self.seq_num,
        )

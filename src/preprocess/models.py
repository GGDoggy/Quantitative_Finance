from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.dataset_artifacts import DatasetLocator as PlotDatasetLocator
from src.dataset_artifacts import PreprocessedArtifact as PreprocessedDataset
from src.raw_batches import RawBatch


class RawBatchLike(Protocol):
    init_path: object
    updates_path: object
    trade_path: object
    timestamp: str


@dataclass(frozen=True)
class PreprocessContext:
    batch: RawBatchLike
    time_step: float
    init_rows: list[list[float]]
    updates_rows: list[list[float]]
    trade_rows: list[list[float]]

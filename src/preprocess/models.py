from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping, Protocol


class RawBatchLike(Protocol):
    init_path: Path
    updates_path: Path
    trade_path: Path
    timestamp: str


def _parse_timestamp(value: str):
    from .datasets import parse_timestamp

    return parse_timestamp(value)


def _format_time_step(value: float) -> str:
    from .datasets import format_time_step

    return format_time_step(value)


@dataclass(frozen=True)
class RawBatch:
    product_id: str
    timestamp: str
    init_path: Path
    updates_path: Path
    trade_path: Path
    is_preprocessed: bool = False

    @property
    def batch_id(self) -> str:
        return f"{self.product_id}|{self.timestamp}"

    @property
    def display_name(self) -> str:
        formatted = _parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        suffix = " | preprocessed" if self.is_preprocessed else ""
        return f"{self.product_id} | {formatted}{suffix}"


@dataclass(frozen=True)
class PlotDatasetLocator:
    product_id: str
    timestamp: str
    time_step: float
    preprocessed_dir: Path
    time_step_token: str | None = None
    resolved_time: float | None = None
    resolved_time_token: str | None = None
    algorithm_name: str | None = None
    original_path: Path | None = None
    simulation_path: Path | None = None
    payload_cache: MutableMapping[Path, dict[str, object]] | None = field(
        default=None,
        compare=False,
        hash=False,
        repr=False,
    )

    @property
    def base_id(self) -> str:
        time_step_token = self.time_step_token or _format_time_step(self.time_step)
        return f"{self.product_id}-{self.timestamp}-{time_step_token}"

    @property
    def path(self) -> Path:
        if self.original_path is not None:
            return self.original_path
        return self.preprocessed_dir / f"{self.base_id}-orderbook_for_plot.npz"


@dataclass(frozen=True)
class PreprocessedDataset:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]
    time_step_token: str | None = None
    resolved_time: float | None = None
    resolved_time_token: str | None = None
    algorithm_name: str | None = None
    simulation_path: Path | None = None

    @property
    def dataset_id(self) -> str:
        if self.simulation_path is not None:
            return f"{self.path}#{self.simulation_path.name}"
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = _parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views)
        simulation_suffix = (
            f" | {self.simulation_path.stem}"
            if self.simulation_path is not None
            else ""
        )
        return (
            f"{self.product_id} | {formatted} | {_format_time_step(self.time_step)}s"
            f"{simulation_suffix} | {views}"
        )

    def to_locator(
        self,
        preprocessed_dir: Path,
        payload_cache: MutableMapping[Path, dict[str, object]] | None = None,
    ) -> PlotDatasetLocator:
        return PlotDatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            time_step=self.time_step,
            preprocessed_dir=preprocessed_dir,
            time_step_token=self.time_step_token,
            resolved_time=self.resolved_time,
            resolved_time_token=self.resolved_time_token,
            algorithm_name=self.algorithm_name,
            original_path=self.path,
            simulation_path=self.simulation_path,
            payload_cache=payload_cache,
        )


@dataclass(frozen=True)
class PreprocessContext:
    batch: RawBatchLike
    time_step: float
    init_rows: list[list[float]]
    updates_rows: list[list[float]]
    trade_rows: list[list[float]]

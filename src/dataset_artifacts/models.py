from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import MutableMapping


def _parse_timestamp(value: str):
    from src.raw_batches import parse_timestamp

    return parse_timestamp(value)


def _format_time_step(value: float) -> str:
    from .naming import format_time_step

    return format_time_step(value)


@dataclass(frozen=True)
class SimulationArtifact:
    product_id: str
    timestamp: str
    time_step: float
    algorithm_name: str
    path: Path
    time_step_token: str | None = None
    resolved_time: float | None = None
    resolved_time_token: str | None = None


@dataclass(frozen=True)
class PreprocessedArtifact:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]
    time_step_token: str | None = None
    simulation_artifact: SimulationArtifact | None = None

    @property
    def resolved_time(self) -> float | None:
        if self.simulation_artifact is None:
            return None
        return self.simulation_artifact.resolved_time

    @property
    def resolved_time_token(self) -> str | None:
        if self.simulation_artifact is None:
            return None
        return self.simulation_artifact.resolved_time_token

    @property
    def algorithm_name(self) -> str | None:
        if self.simulation_artifact is None:
            return None
        return self.simulation_artifact.algorithm_name

    @property
    def simulation_path(self) -> Path | None:
        if self.simulation_artifact is None:
            return None
        return self.simulation_artifact.path

    @property
    def dataset_id(self) -> str:
        if self.simulation_artifact is not None:
            return f"{self.path}#{self.simulation_artifact.path.name}"
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = _parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views)
        simulation_suffix = (
            f" | {self.simulation_artifact.path.stem}"
            if self.simulation_artifact is not None
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
    ) -> "DatasetLocator":
        return DatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            time_step=self.time_step,
            preprocessed_dir=preprocessed_dir,
            time_step_token=self.time_step_token,
            original_path=self.path,
            simulation_artifact=self.simulation_artifact,
            payload_cache=payload_cache,
        )


@dataclass(frozen=True)
class DatasetLocator:
    product_id: str
    timestamp: str
    time_step: float
    preprocessed_dir: Path
    time_step_token: str | None = None
    original_path: Path | None = None
    simulation_artifact: SimulationArtifact | None = None
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

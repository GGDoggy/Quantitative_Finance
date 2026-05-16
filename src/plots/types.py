from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PlotDatasetLocator(Protocol):
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str | None
    resolved_time: float | None
    resolved_time_token: str | None
    algorithm_name: str | None
    preprocessed_dir: Path
    simulation_path: Path | None

    @property
    def base_id(self) -> str: ...

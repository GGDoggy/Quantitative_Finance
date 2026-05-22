from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .options import PlotRenderOptions


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


@runtime_checkable
class PlotBuilder(Protocol):
    def __call__(
        self,
        locators: list[PlotDatasetLocator],
        render_options: PlotRenderOptions | None = None,
    ) -> object: ...

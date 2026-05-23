"""Plot modules package."""

from src.preprocess.exceptions import PreprocessedDataError
from .registry import PLOT_LABELS, PLOT_REGISTRY, PlotSpec
from .settings import (
    DashboardSimulationHeatmapSettings,
    PlotRenderOptions,
)

"""Deprecated shim module for legacy ``src.plots`` imports.

Register plot types with their lazy plot and preprocess builders.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.app_plot_registry import APP_PLOT_LABELS, APP_PLOT_REGISTRY
from src.plotlib import PlotBuilder
from src.preprocess.registry import PREPROCESS_PLOT_REGISTRY


PreprocessBuilder = Callable[[object], dict[str, object]]


@dataclass(frozen=True)
class PlotSpec:
    key: str
    label: str
    plot_builder: PlotBuilder
    preprocess_builder: PreprocessBuilder | None
    required_payload_keys: tuple[str, ...]

PLOT_REGISTRY: dict[str, PlotSpec] = {}
for plot_id, entry in APP_PLOT_REGISTRY.items():
    preprocess_spec = PREPROCESS_PLOT_REGISTRY.get(plot_id)
    PLOT_REGISTRY[plot_id] = PlotSpec(
        key=plot_id,
        label=entry.label,
        plot_builder=entry.builder,
        preprocess_builder=(
            preprocess_spec.preprocess_builder if preprocess_spec is not None else None
        ),
        required_payload_keys=(
            preprocess_spec.required_payload_keys
            if preprocess_spec is not None
            else ("__simulation_npz__",)
        ),
    )

PLOT_LABELS = dict(APP_PLOT_LABELS)

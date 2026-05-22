"""Adapters for discovering plot views from the plot registry."""
from __future__ import annotations

from typing import Iterable


class PlotRegistryViewDetector:
    """Detect available views by matching payload keys to plot registry specs."""

    def __init__(self, plot_registry: dict[str, object]):
        self._plot_registry = plot_registry

    def __call__(self, data_keys: Iterable[str]) -> tuple[str, ...]:
        keys = set(data_keys)
        return tuple(
            key
            for key, spec in self._plot_registry.items()
            if set(spec.required_payload_keys).issubset(keys)
        )

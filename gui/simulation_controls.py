"""Simulation heatmap control parsing, validation, and state synchronization."""

from __future__ import annotations

import json
import math

from src.plotlib import DashboardSimulationHeatmapSettings
from src.plotlib.options import (
    ConditionalFillProbabilityPlotSettings,
    FillProbabilityPlotSettings,
    HeatmapAxisSettings,
    ManualColorRange,
    OptionalColorRange,
    OptionalSymmetricColorRange,
    ProfitPlotSettings,
)

from .styles import SIMULATION_SETTINGS_GROUP_BY_PLOT


class SimulationControlsMixin:
    """Encapsulate simulation heatmap settings lifecycle and widget sync."""

    def _load_dashboard_settings(self) -> DashboardSimulationHeatmapSettings:
        """Load persisted heatmap settings or return defaults."""
        if not self.dashboard_settings_path.exists():
            return DashboardSimulationHeatmapSettings()
        try:
            payload = json.loads(self.dashboard_settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DashboardSimulationHeatmapSettings()
        return DashboardSimulationHeatmapSettings.from_dict(payload)

    def _save_dashboard_settings(self) -> None:
        """Persist the current heatmap settings to the JSON settings file."""
        payload = self._simulation_heatmap_settings.to_dict()
        self.dashboard_settings_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _simulation_settings_group_key(self, plot_type: str | None) -> str | None:
        """Map a plot type to its heatmap settings group key."""
        if plot_type is None:
            return None
        return SIMULATION_SETTINGS_GROUP_BY_PLOT.get(plot_type)

    def _selected_simulation_settings_group_key(self) -> str | None:
        """Return the settings group key for the currently selected plot."""
        return self._simulation_settings_group_key(self._selected_plot_type())

    def _simulation_group_settings(
        self, group_key: str
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
    ):
        """Return the heatmap settings object for a named group."""
        return getattr(self._simulation_heatmap_settings, group_key)

    def _selected_simulation_group_settings(
        self,
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
        | None
    ):
        """Return the heatmap settings for the selected plot, if applicable."""
        group_key = self._selected_simulation_settings_group_key()
        if group_key is None:
            return None
        return self._simulation_group_settings(group_key)

    def _replace_simulation_group_settings(
        self,
        group_key: str,
        settings: (
            FillProbabilityPlotSettings
            | ProfitPlotSettings
            | ConditionalFillProbabilityPlotSettings
        ),
    ) -> None:
        """Replace one settings group while preserving the others."""
        current = self._simulation_heatmap_settings
        self._simulation_heatmap_settings = DashboardSimulationHeatmapSettings(
            fill_probability=(
                settings
                if group_key == "fill_probability"
                else current.fill_probability
            ),
            profit=settings if group_key == "profit" else current.profit,
            conditional_fill_probability=(
                settings
                if group_key == "conditional_fill_probability"
                else current.conditional_fill_probability
            ),
        )

    @staticmethod
    def _read_required_positive_int(value: object, label: str) -> int:
        """Parse and validate a required positive integer input."""
        if value is None:
            raise ValueError(f"{label} is required.")
        number = int(value)
        if number <= 0:
            raise ValueError(f"{label} must be a positive integer.")
        return number

    @staticmethod
    def _read_required_finite_float(value: object, label: str) -> float:
        """Parse and validate a required finite float input."""
        if value is None:
            raise ValueError(f"{label} is required.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{label} must be finite.")
        return number

    def _validate_axis_settings(
        self,
        *,
        size_min: float,
        size_max: float,
        shared_bins: int,
        use_log_bins: bool,
    ) -> HeatmapAxisSettings:
        """Validate heatmap axis controls and build the axis settings object."""
        if size_min >= size_max:
            raise ValueError("Size min must be smaller than size max.")
        if use_log_bins and (size_min <= 0 or size_max <= 0):
            raise ValueError("Size range must be > 0 when log bins are enabled.")
        if shared_bins <= 0:
            raise ValueError("Bins must be a positive integer.")
        return HeatmapAxisSettings(
            size_min=size_min,
            size_max=size_max,
            shared_bins=shared_bins,
            use_log_bins=use_log_bins,
        )

    def _build_settings_from_controls(
        self, group_key: str
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
    ):
        """Build a settings object from the current widget values."""
        size_min = self._read_required_finite_float(
            self.simulation_size_min_input.value, "Size min"
        )
        size_max = self._read_required_finite_float(
            self.simulation_size_max_input.value, "Size max"
        )
        shared_bins = self._read_required_positive_int(
            self.simulation_bins_input.value, "Bins"
        )
        axis = self._validate_axis_settings(
            size_min=size_min,
            size_max=size_max,
            shared_bins=shared_bins,
            use_log_bins=bool(self.simulation_log_checkbox.value),
        )

        sample_auto = bool(self.sample_color_auto_checkbox.value)
        if sample_auto:
            sample_count_range = OptionalColorRange(auto=True)
        else:
            sample_min = self._read_required_finite_float(
                self.sample_color_min_input.value, "Sample-count color min"
            )
            sample_max = self._read_required_finite_float(
                self.sample_color_max_input.value, "Sample-count color max"
            )
            if sample_min < 0 or sample_max < 0:
                raise ValueError("Sample-count color bounds must be non-negative.")
            if sample_min >= sample_max:
                raise ValueError(
                    "Sample-count color min must be smaller than sample-count color max."
                )
            sample_count_range = OptionalColorRange(
                auto=False,
                min=sample_min,
                max=sample_max,
            )

        if group_key == "profit":
            metric_auto = bool(self.metric_color_auto_checkbox.value)
            if metric_auto:
                metric_limit = OptionalSymmetricColorRange(auto=True)
            else:
                limit = self._read_required_finite_float(
                    self.metric_color_limit_input.value, "Metric color limit"
                )
                if limit <= 0:
                    raise ValueError("Metric color limit must be greater than 0.")
                metric_limit = OptionalSymmetricColorRange(auto=False, limit=limit)
            return ProfitPlotSettings(
                axis=axis,
                metric_limit=metric_limit,
                sample_count_range=sample_count_range,
            )

        metric_min = self._read_required_finite_float(
            self.metric_color_min_input.value, "Metric color min"
        )
        metric_max = self._read_required_finite_float(
            self.metric_color_max_input.value, "Metric color max"
        )
        if metric_min >= metric_max:
            raise ValueError("Metric color min must be smaller than metric color max.")
        metric_range = ManualColorRange(min=metric_min, max=metric_max)

        if group_key == "fill_probability":
            return FillProbabilityPlotSettings(
                axis=axis,
                metric_range=metric_range,
                sample_count_range=sample_count_range,
            )
        return ConditionalFillProbabilityPlotSettings(
            axis=axis,
            metric_range=metric_range,
            sample_count_range=sample_count_range,
        )

    def _sync_simulation_heatmap_settings_controls(self) -> None:
        """Synchronize heatmap control widgets with the selected settings group."""
        plot_type = self._selected_plot_type()
        group_key = self._simulation_settings_group_key(plot_type)
        settings = self._selected_simulation_group_settings()
        is_simulation_heatmap = group_key is not None and settings is not None
        is_profit = group_key == "profit"

        self._updating_controls = True
        try:
            for widget in (
                self.simulation_size_min_input,
                self.simulation_size_max_input,
                self.simulation_bins_input,
                self.simulation_log_checkbox,
                self.metric_color_auto_checkbox,
                self.metric_color_min_input,
                self.metric_color_max_input,
                self.metric_color_limit_input,
                self.sample_color_auto_checkbox,
                self.sample_color_min_input,
                self.sample_color_max_input,
            ):
                widget.visible = is_simulation_heatmap
                widget.disabled = not is_simulation_heatmap

            if not is_simulation_heatmap:
                return

            self.simulation_size_min_input.value = settings.axis.size_min
            self.simulation_size_max_input.value = settings.axis.size_max
            self.simulation_bins_input.value = settings.axis.shared_bins
            self.simulation_log_checkbox.value = settings.axis.use_log_bins

            self.metric_color_auto_checkbox.visible = is_profit
            self.metric_color_auto_checkbox.disabled = not is_profit
            self.metric_color_min_input.visible = not is_profit
            self.metric_color_max_input.visible = not is_profit
            self.metric_color_limit_input.visible = is_profit

            if is_profit:
                profit_settings = settings
                self.metric_color_auto_checkbox.value = profit_settings.metric_limit.auto
                self.metric_color_limit_input.value = (
                    profit_settings.metric_limit.limit
                    if profit_settings.metric_limit.limit is not None
                    else 1.0
                )
                self.metric_color_limit_input.disabled = profit_settings.metric_limit.auto
            else:
                metric_settings = settings.metric_range
                self.metric_color_min_input.value = metric_settings.min
                self.metric_color_max_input.value = metric_settings.max
                self.metric_color_min_input.disabled = False
                self.metric_color_max_input.disabled = False
                self.metric_color_limit_input.disabled = True

            self.sample_color_auto_checkbox.value = settings.sample_count_range.auto
            self.sample_color_min_input.value = (
                settings.sample_count_range.min
                if settings.sample_count_range.min is not None
                else 0.0
            )
            self.sample_color_max_input.value = (
                settings.sample_count_range.max
                if settings.sample_count_range.max is not None
                else 1.0
            )
            self.sample_color_min_input.disabled = settings.sample_count_range.auto
            self.sample_color_max_input.disabled = settings.sample_count_range.auto
        finally:
            self._updating_controls = False

    def _simulation_heatmap_render_settings(
        self,
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
        | None
    ):
        """Return the active settings used to render simulation heatmaps."""
        return self._selected_simulation_group_settings()

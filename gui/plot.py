from __future__ import annotations

import json
import math
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import holoviews as hv
import panel as pn
from plotly.graph_objects import Figure

from src.plots import (
    DashboardSimulationHeatmapSettings,
    PLOT_LABELS,
    PLOT_REGISTRY,
    PlotRenderOptions,
)
from src.plots.settings import (
    ConditionalFillProbabilityPlotSettings,
    FillProbabilityPlotSettings,
    HeatmapAxisSettings,
    ManualColorRange,
    OptionalColorRange,
    OptionalSymmetricColorRange,
    ProfitPlotSettings,
)
from src.preprocess import (
    PlotDatasetLocator,
    PreprocessedDataset,
    RawBatch,
    discover_preprocessed_datasets,
    discover_raw_batches,
    format_time_step,
    parse_timestamp,
    preprocess_batches,
)
from src.simulation import (
    DEFAULT_RESOLVED_TIME,
    DEFAULT_TIME_STEP as DEFAULT_SIMULATION_TIME_STEP,
    TIME_AVERAGED_RANDOM_CANCELLATION_NAME,
    get_algorithm_names,
    simulate_batches,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"
DASHBOARD_SETTINGS_PATH = PROJECT_ROOT / "gui" / "dashboard_settings.json"

DASHBOARD_CSS = """
:root {
  --qf-bg: #020617;
  --qf-surface: #0b1220;
  --qf-surface-elevated: #111827;
  --qf-border: rgba(148, 163, 184, 0.22);
  --qf-primary: #22d3ee;
  --qf-accent: #3b82f6;
  --qf-success: #22c55e;
  --qf-warning: #f59e0b;
  --qf-danger: #f43f5e;
  --qf-text: #e5eefb;
  --qf-muted: #94a3b8;
}

body, .bk, .pn-template {
  background: radial-gradient(circle at top left, rgba(34, 211, 238, 0.10), transparent 28rem),
    linear-gradient(135deg, #020617 0%, #07111f 45%, #030712 100%) !important;
  color: var(--qf-text) !important;
}

.pn-template .pn-wrapper, .pn-template .main {
  background: transparent !important;
}

.qf-dashboard-header {
  padding: 1rem 1.25rem;
  border: 1px solid var(--qf-border);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(17, 24, 39, 0.88));
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.32);
}

.qf-eyebrow {
  margin: 0 0 0.35rem;
  color: var(--qf-primary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.qf-title h1, .qf-section-title h2 {
  margin: 0;
  color: #f8fafc;
}

.qf-title p, .qf-section-subtitle {
  color: var(--qf-muted);
}

.qf-card {
  border: 1px solid var(--qf-border) !important;
  border-radius: 16px !important;
  background: rgba(15, 23, 42, 0.78) !important;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.24) !important;
  backdrop-filter: blur(14px);
  overflow: visible !important;
}

.qf-card .card-header {
  border-bottom: 1px solid var(--qf-border) !important;
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.12), rgba(59, 130, 246, 0.08)) !important;
  color: #f8fafc !important;
  font-weight: 700;
}

.qf-card .card-body {
  padding: 1rem !important;
  overflow: visible !important;
}

.qf-plot-controls {
  position: relative;
  z-index: 30;
}

.qf-button-row {
  gap: 0.75rem;
  justify-content: flex-end;
}

.qf-plot-workspace {
  min-height: 620px;
  position: relative;
  z-index: 1;
}

.qf-main-plot-card {
  min-height: 620px;
}

.qf-plot-result {
  min-height: 560px;
  width: 100%;
}

.qf-fill-probability-card {
  min-height: 1660px;
}

.qf-fill-probability-result {
  min-height: 1560px;
}

.qf-plot-tabs {
  width: 100%;
}

.qf-status-card .alert-success {
  border-color: rgba(34, 197, 94, 0.45);
}

.qf-status-card .alert-warning {
  border-color: rgba(245, 158, 11, 0.55);
}

.qf-status-card .alert-danger {
  border-color: rgba(244, 63, 94, 0.55);
}

.qf-card button, .qf-dashboard-header button {
  border-radius: 999px !important;
  font-weight: 700 !important;
}

.qf-card label, .qf-card .bk-input-group label {
  color: var(--qf-muted) !important;
  font-weight: 650;
}

.qf-card .bk-input, .qf-card .bk-input-group, .qf-card select {
  color: var(--qf-text) !important;
}

@media (max-width: 900px) {
  .qf-dashboard-header {
    padding: 0.9rem;
  }

  .qf-responsive-row {
    flex-direction: column !important;
    align-items: stretch !important;
  }

  .qf-plot-workspace, .qf-main-plot-card {
    min-height: 460px;
  }

  .qf-plot-result {
    min-height: 420px;
  }

  .qf-fill-probability-card {
    min-height: 1320px;
  }

  .qf-fill-probability-result {
    min-height: 1240px;
  }
}
"""

PLOTLY_DARK_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(2, 6, 23, 0)",
    "plot_bgcolor": "rgba(15, 23, 42, 0.92)",
    "font": {"color": "#e5eefb"},
    "margin": {"l": 56, "r": 32, "t": 54, "b": 48},
}

PRODUCT_PLACEHOLDER = "Select a product..."
PLOT_PLACEHOLDER = "Select a plot..."
TIMESTAMP_PLACEHOLDER = "Select a timestamp..."
FILL_GROUP_PLACEHOLDER = "Select a simulation group..."
SIMULATION_HEATMAP_PLOT_TYPES = {
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
}
COST_FILTERED_PLOT_TYPES = {
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
}
SIMULATION_SETTINGS_GROUP_BY_PLOT = {
    "fill_probability": "fill_probability",
    "mid_profit": "profit",
    "micro_profit": "profit",
    "mid_fill_probability_cost": "conditional_fill_probability",
    "micro_fill_probability_cost": "conditional_fill_probability",
}


class OrderbookDashboard:
    def __init__(self, raw_dir: Path, preprocessed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.preprocessed_dir = preprocessed_dir
        self.dashboard_settings_path = DASHBOARD_SETTINGS_PATH
        self._raw_dir_input_value = self._display_raw_dir(raw_dir)
        self._simulation_heatmap_settings = self._load_dashboard_settings()
        self.preprocessed_by_label: dict[str, PreprocessedDataset] = {}
        self.preprocessed_datasets: list[PreprocessedDataset] = []
        self.raw_by_label: dict[str, RawBatch] = {}
        self.all_raw_by_label: dict[str, RawBatch] = {}
        self._updating_controls = False
        self.status = pn.pane.Alert(
            "Ready.", alert_type="light", sizing_mode="stretch_width"
        )
        self.product_select = pn.widgets.Select(
            name="Product",
            options=[],
            sizing_mode="stretch_width",
        )
        self.raw_dir_input = pn.widgets.TextInput(
            name="Raw data directory",
            value=self._raw_dir_input_value,
            placeholder="data/v3 or D:\\market\\raw",
            sizing_mode="stretch_width",
        )
        self.apply_raw_dir_button = pn.widgets.Button(
            name="Apply Raw Path",
            button_type="default",
            width=170,
        )
        self.raw_select = pn.widgets.MultiChoice(
            name="Raw batches pending preprocess",
            options=[],
            sizing_mode="stretch_width",
            min_height=180,
        )
        self.simulation_raw_select = pn.widgets.MultiChoice(
            name="Raw batches for simulation",
            options=[],
            sizing_mode="stretch_width",
            min_height=180,
        )
        self.simulation_select_all_button = pn.widgets.Button(
            name="Select All",
            button_type="default",
            sizing_mode="stretch_width",
        )
        self.simulation_clear_selection_button = pn.widgets.Button(
            name="Clear Selection",
            button_type="light",
            sizing_mode="stretch_width",
        )
        self.simulation_algorithm_select = pn.widgets.Select(
            name="Simulation algorithm",
            options=get_algorithm_names(),
            value=(get_algorithm_names()[0] if get_algorithm_names() else None),
            sizing_mode="stretch_width",
        )
        self.simulation_resolved_time_input = pn.widgets.FloatInput(
            name="Resolved time",
            value=DEFAULT_RESOLVED_TIME,
            step=0.1,
            start=0,
            sizing_mode="stretch_width",
        )
        self.simulation_time_step_input = pn.widgets.FloatInput(
            name="Simulation time step",
            value=DEFAULT_SIMULATION_TIME_STEP,
            step=0.01,
            start=0.00000001,
            sizing_mode="stretch_width",
            visible=False,
        )
        self.plot_select = pn.widgets.Select(
            name="Plot",
            options=[],
            sizing_mode="stretch_width",
        )
        self.timestamp_select = pn.widgets.Select(
            name="Timestamp",
            options=[],
            sizing_mode="stretch_width",
        )
        self.fill_group_select = pn.widgets.Select(
            name="Simulation group",
            options={},
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.cost_input = pn.widgets.TextInput(
            name="Cost",
            value="0",
            placeholder="Enter a finite cost value",
            sizing_mode="stretch_width",
            visible=False,
        )
        self.simulation_size_min_input = pn.widgets.FloatInput(
            name="Size min",
            value=1e-3,
            step=0.001,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.simulation_size_max_input = pn.widgets.FloatInput(
            name="Size max",
            value=10.0,
            step=0.1,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.simulation_bins_input = pn.widgets.IntInput(
            name="Bins",
            value=20,
            step=1,
            start=1,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.simulation_log_checkbox = pn.widgets.Checkbox(
            name="Use log bins and axes",
            value=True,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.metric_color_auto_checkbox = pn.widgets.Checkbox(
            name="Auto metric color range",
            value=True,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.metric_color_min_input = pn.widgets.FloatInput(
            name="Metric color min",
            value=0.0,
            step=0.01,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.metric_color_max_input = pn.widgets.FloatInput(
            name="Metric color max",
            value=1.0,
            step=0.01,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.metric_color_limit_input = pn.widgets.FloatInput(
            name="Metric color limit",
            value=1.0,
            step=0.01,
            start=0.0,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.sample_color_auto_checkbox = pn.widgets.Checkbox(
            name="Auto sample-count color range",
            value=True,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.sample_color_min_input = pn.widgets.FloatInput(
            name="Sample-count color min",
            value=0.0,
            step=1.0,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.sample_color_max_input = pn.widgets.FloatInput(
            name="Sample-count color max",
            value=1.0,
            step=1.0,
            sizing_mode="stretch_width",
            visible=False,
            disabled=True,
        )
        self.refresh_button = pn.widgets.Button(
            name="Refresh Catalog",
            button_type="default",
            width=170,
        )
        self.preprocess_button = pn.widgets.Button(
            name="Preprocess Selected",
            button_type="primary",
            sizing_mode="stretch_width",
        )
        self.preprocess_spinner = pn.indicators.LoadingSpinner(
            value=False,
            width=24,
            height=24,
            color="primary",
            visible=False,
        )
        self.dataset_summary = pn.pane.Markdown(
            "No preprocessed datasets discovered.",
            sizing_mode="stretch_width",
        )
        self.raw_summary = pn.pane.Markdown(
            "No raw batches discovered.",
            sizing_mode="stretch_width",
        )
        self.preprocess_progress = pn.pane.Markdown(
            "No preprocess job running.",
            sizing_mode="stretch_width",
        )
        self.simulation_button = pn.widgets.Button(
            name="Run Simulation",
            button_type="primary",
            sizing_mode="stretch_width",
        )
        self.simulation_spinner = pn.indicators.LoadingSpinner(
            value=False,
            width=24,
            height=24,
            color="primary",
            visible=False,
        )
        self.simulation_progress = pn.pane.Markdown(
            "No simulation job running.",
            sizing_mode="stretch_width",
        )
        self.plot_area = pn.Column(
            pn.pane.Markdown(
                "Select a product, plot, and timestamp to start plotting."
            ),
            sizing_mode="stretch_both",
            min_width=720,
        )

        self.refresh_button.on_click(self._handle_refresh)
        self.apply_raw_dir_button.on_click(self._handle_apply_raw_dir)
        self.preprocess_button.on_click(self._handle_preprocess)
        self.simulation_select_all_button.on_click(self._handle_simulation_select_all)
        self.simulation_clear_selection_button.on_click(
            self._handle_simulation_clear_selection
        )
        self.simulation_button.on_click(self._handle_simulation)
        self.product_select.param.watch(self._handle_product_change, "value")
        self.raw_select.param.watch(self._handle_raw_selection_change, "value")
        self.simulation_algorithm_select.param.watch(
            self._handle_simulation_algorithm_change, "value"
        )
        self.simulation_raw_select.param.watch(
            self._handle_simulation_raw_selection_change, "value"
        )
        self.plot_select.param.watch(self._handle_plot_change, "value")
        self.timestamp_select.param.watch(self._handle_timestamp_change, "value")
        self.fill_group_select.param.watch(self._handle_fill_group_change, "value")
        self.cost_input.param.watch(self._handle_cost_change, "value")
        self.simulation_size_min_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.simulation_size_max_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.simulation_bins_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.simulation_log_checkbox.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.metric_color_auto_checkbox.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.metric_color_min_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.metric_color_max_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.metric_color_limit_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.sample_color_auto_checkbox.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.sample_color_min_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )
        self.sample_color_max_input.param.watch(
            self._handle_simulation_heatmap_setting_change, "value"
        )

        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        datasets = discover_preprocessed_datasets(self.preprocessed_dir)
        batches = discover_raw_batches(self.raw_dir, self.preprocessed_dir)
        self.preprocessed_datasets = datasets
        self.preprocessed_by_label = {
            dataset.display_name: dataset for dataset in datasets
        }
        self.all_raw_by_label = {
            batch.display_name: batch for batch in batches
        }
        self.raw_by_label = {
            batch.display_name: batch for batch in batches if not batch.is_preprocessed
        }

        existing_raw = [
            label for label in self.raw_select.value if label in self.raw_by_label
        ]
        self.raw_select.options = list(self.raw_by_label.keys())
        self.raw_select.value = existing_raw
        existing_simulation_raw = [
            label
            for label in self.simulation_raw_select.value
            if label in self.all_raw_by_label
        ]
        self.simulation_raw_select.options = list(self.all_raw_by_label.keys())
        self.simulation_raw_select.value = existing_simulation_raw

        previous_product = self._selected_product()
        product_options = self._available_products()
        next_product = previous_product if previous_product in product_options else None
        product_select_options = self._with_placeholder_options(
            {product_id: product_id for product_id in product_options},
            PRODUCT_PLACEHOLDER,
        )

        self._updating_controls = True
        try:
            if self.product_select.options != product_select_options:
                self.product_select.options = product_select_options
            if self.product_select.value != next_product:
                self.product_select.value = next_product
            self._sync_plot_options(render=False)
        finally:
            self._updating_controls = False

        self._update_raw_summary()
        self._sync_simulation_parameter_visibility()
        self._render_plots()

    def _resolve_raw_dir(self, raw_dir_value: str) -> Path:
        candidate = Path(raw_dir_value.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            raise ValueError(f"Raw data directory does not exist: {candidate}")
        if not candidate.is_dir():
            raise ValueError(f"Raw data directory is not a directory: {candidate}")
        return candidate

    def _display_raw_dir(self, raw_dir: Path) -> str:
        try:
            return str(raw_dir.resolve().relative_to(PROJECT_ROOT))
        except ValueError:
            return str(raw_dir.resolve())

    def _set_status(self, message: str, level: str = "light") -> None:
        self.status.object = message
        self.status.alert_type = level

    def _load_dashboard_settings(self) -> DashboardSimulationHeatmapSettings:
        if not self.dashboard_settings_path.exists():
            return DashboardSimulationHeatmapSettings()
        try:
            payload = json.loads(self.dashboard_settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DashboardSimulationHeatmapSettings()
        return DashboardSimulationHeatmapSettings.from_dict(payload)

    def _save_dashboard_settings(self) -> None:
        payload = self._simulation_heatmap_settings.to_dict()
        self.dashboard_settings_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _simulation_settings_group_key(self, plot_type: str | None) -> str | None:
        if plot_type is None:
            return None
        return SIMULATION_SETTINGS_GROUP_BY_PLOT.get(plot_type)

    def _selected_simulation_settings_group_key(self) -> str | None:
        return self._simulation_settings_group_key(self._selected_plot_type())

    def _simulation_group_settings(
        self, group_key: str
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
    ):
        return getattr(self._simulation_heatmap_settings, group_key)

    def _selected_simulation_group_settings(
        self,
    ) -> (
        FillProbabilityPlotSettings
        | ProfitPlotSettings
        | ConditionalFillProbabilityPlotSettings
        | None
    ):
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
        if value is None:
            raise ValueError(f"{label} is required.")
        number = int(value)
        if number <= 0:
            raise ValueError(f"{label} must be a positive integer.")
        return number

    def _validate_axis_settings(
        self,
        *,
        size_min: float,
        size_max: float,
        shared_bins: int,
        use_log_bins: bool,
    ) -> HeatmapAxisSettings:
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
        return self._selected_simulation_group_settings()

    def _handle_refresh(self, _event) -> None:
        self.refresh_catalog()
        self._set_status(
            f"Catalog refreshed from raw directory: {self.raw_dir}", "success"
        )

    def _handle_apply_raw_dir(self, _event) -> None:
        raw_dir_value = self.raw_dir_input.value.strip()
        if not raw_dir_value:
            self.raw_dir_input.value = self._raw_dir_input_value
            self._set_status("Raw data directory is required.", "danger")
            return

        try:
            next_raw_dir = self._resolve_raw_dir(raw_dir_value)
        except ValueError as error:
            self.raw_dir_input.value = self._raw_dir_input_value
            self._set_status(str(error), "danger")
            return

        self.raw_dir = next_raw_dir
        self._raw_dir_input_value = self._display_raw_dir(next_raw_dir)
        self.raw_dir_input.value = self._raw_dir_input_value
        self.refresh_catalog()
        self._set_status(
            f"Raw data directory updated to: {self.raw_dir}", "success"
        )

    def _set_preprocess_loading(self, is_loading: bool) -> None:
        self.preprocess_button.disabled = is_loading
        self.preprocess_button.loading = is_loading
        self.preprocess_spinner.value = is_loading
        self.preprocess_spinner.visible = is_loading
        self.preprocess_progress.loading = is_loading

    def _set_simulation_loading(self, is_loading: bool) -> None:
        self.simulation_button.disabled = is_loading
        self.simulation_button.loading = is_loading
        self.simulation_spinner.value = is_loading
        self.simulation_spinner.visible = is_loading
        self.simulation_progress.loading = is_loading

    def _format_preprocess_progress(
        self, batch_count: int, progress_messages: list[str]
    ) -> str:
        progress_lines = "\n".join(
            f"- {progress_message}" for progress_message in progress_messages
        )
        return (
            f"**Processing batch count:** {batch_count}\n\n"
            f"**Progress**\n{progress_lines}"
        )

    def _format_simulation_progress(
        self, batch_count: int, progress_messages: list[str]
    ) -> str:
        progress_lines = "\n".join(
            f"- {progress_message}" for progress_message in progress_messages
        )
        return (
            f"**Simulation batch count:** {batch_count}\n\n"
            f"**Progress**\n{progress_lines}"
        )

    @staticmethod
    def _read_required_finite_float(value: object, label: str) -> float:
        if value is None:
            raise ValueError(f"{label} is required.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{label} must be finite.")
        return number

    def _handle_preprocess(self, _event) -> None:
        selected_batches = [
            self.raw_by_label[label]
            for label in self.raw_select.value
            if label in self.raw_by_label
        ]
        if not selected_batches:
            self.preprocess_progress.object = "No preprocess job running."
            self._set_status(
                "Select at least one raw batch before preprocessing.", "warning"
            )
            return

        batch_count = len(selected_batches)
        progress_messages = [f"Queued {batch_count} raw batch(es) for preprocessing."]
        self.preprocess_progress.object = self._format_preprocess_progress(
            batch_count, progress_messages
        )
        self._set_status(f"Preprocessing {batch_count} raw batch(es)...", "primary")
        self._set_preprocess_loading(True)
        try:

            def update_progress(message: str) -> None:
                progress_messages.append(message)
                self.preprocess_progress.object = self._format_preprocess_progress(
                    batch_count, progress_messages
                )
                self._set_status(message, "primary")

            preprocessed_datasets = preprocess_batches(
                selected_batches,
                output_dir=self.preprocessed_dir,
                progress_callback=update_progress,
            )
            self.refresh_catalog()
            generated_paths = {dataset.path for dataset in preprocessed_datasets}
            target_dataset = next(
                (
                    dataset
                    for dataset in reversed(self.preprocessed_datasets)
                    if dataset.path in generated_paths
                ),
                None,
            )
            if target_dataset is not None:
                self._select_preprocessed_dataset(target_dataset)
            summary = (
                f"Completed preprocessing {batch_count} batch(es). "
                f"Generated {len(preprocessed_datasets)} preprocessed dataset(s)."
            )
            progress_messages.append(summary)
            self.preprocess_progress.object = self._format_preprocess_progress(
                batch_count, progress_messages
            )
            self._set_status(summary, "success")
        except Exception as error:
            error_message = f"Preprocess failed: {error}"
            progress_messages.append(error_message)
            self.preprocess_progress.object = self._format_preprocess_progress(
                batch_count, progress_messages
            )
            self._set_status(error_message, "danger")
        finally:
            self._set_preprocess_loading(False)

    def _handle_simulation(self, _event) -> None:
        selected_batches = [
            self.all_raw_by_label[label]
            for label in self.simulation_raw_select.value
            if label in self.all_raw_by_label
        ]
        if not selected_batches:
            self.simulation_progress.object = "No simulation job running."
            self._set_status(
                "Select at least one raw batch before running simulation.", "warning"
            )
            return

        algorithm_name = self.simulation_algorithm_select.value
        batch_count = len(selected_batches)
        progress_messages: list[str] = []
        self._set_simulation_loading(True)
        try:
            resolved_time = self._read_required_finite_float(
                self.simulation_resolved_time_input.value,
                "Simulation resolved_time",
            )
            time_step = self._read_required_finite_float(
                self.simulation_time_step_input.value,
                "Simulation time_step",
            )
            progress_messages.append(
                (
                    f"Queued {batch_count} raw batch(es) for simulation with "
                    f"{algorithm_name}, resolved_time={resolved_time}, time_step={time_step}."
                )
            )
            self.simulation_progress.object = self._format_simulation_progress(
                batch_count, progress_messages
            )
            self._set_status(
                f"Running simulation for {batch_count} raw batch(es)...", "primary"
            )

            def update_progress(message: str) -> None:
                progress_messages.append(message)
                self.simulation_progress.object = self._format_simulation_progress(
                    batch_count, progress_messages
                )
                self._set_status(message, "primary")

            simulation_results = simulate_batches(
                selected_batches,
                output_dir=self.preprocessed_dir,
                algorithm_name=str(algorithm_name),
                time_step=time_step,
                resolved_time=resolved_time,
                progress_callback=update_progress,
            )
            overwritten_count = sum(
                1 for simulation_result in simulation_results if simulation_result.overwritten
            )
            self.refresh_catalog()
            generated_paths = {
                simulation_result.output_path for simulation_result in simulation_results
            }
            target_dataset = next(
                (
                    dataset
                    for dataset in reversed(self.preprocessed_datasets)
                    if dataset.simulation_path in generated_paths
                ),
                None,
            )
            if target_dataset is not None:
                self._select_fill_probability_dataset(target_dataset)
            summary = (
                f"Completed simulation for {batch_count} batch(es). "
                f"Generated {len(simulation_results)} simulation file(s). "
                f"Overwrote {overwritten_count} existing file(s)."
            )
            progress_messages.append(summary)
            self.simulation_progress.object = self._format_simulation_progress(
                batch_count, progress_messages
            )
            self._set_status(summary, "success")
        except Exception as error:
            error_message = f"Simulation failed: {error}"
            progress_messages.append(error_message)
            self.simulation_progress.object = self._format_simulation_progress(
                batch_count, progress_messages
            )
            self._set_status(error_message, "danger")
        finally:
            self._set_simulation_loading(False)

    def _select_preprocessed_dataset(self, dataset: PreprocessedDataset) -> None:
        if dataset.product_id not in self._selectable_option_values(
            self.product_select.options
        ):
            return

        preferred_plot_type = next(
            (
                view
                for view in dataset.available_views
                if view in PLOT_REGISTRY
                and view not in SIMULATION_HEATMAP_PLOT_TYPES
            ),
            next(
                (view for view in dataset.available_views if view in PLOT_REGISTRY),
                None,
            ),
        )
        preferred_plot_label = (
            self._plot_label_for_type(preferred_plot_type)
            if preferred_plot_type is not None
            else None
        )

        self._updating_controls = True
        try:
            if self.product_select.value != dataset.product_id:
                self.product_select.value = dataset.product_id
        finally:
            self._updating_controls = False

        self._sync_plot_options(render=False)
        if (
            preferred_plot_label is not None
            and preferred_plot_label in self.plot_select.options
        ):
            self._updating_controls = True
            try:
                if self.plot_select.value != preferred_plot_label:
                    self.plot_select.value = preferred_plot_label
            finally:
                self._updating_controls = False
            self._sync_timestamp_options(render=False)

        dataset_key = self._dataset_selection_key(dataset)
        if dataset_key in set(self.timestamp_select.options.values()):
            self._updating_controls = True
            try:
                if self.timestamp_select.value != dataset_key:
                    self.timestamp_select.value = dataset_key
            finally:
                self._updating_controls = False
        elif (
            preferred_plot_type is not None
            and preferred_plot_type in SIMULATION_HEATMAP_PLOT_TYPES
        ):
            group_value = self._simulation_group_value(
                self._simulation_group_key(dataset)
            )
            if group_value in set(self.fill_group_select.options.values()):
                self._updating_controls = True
                try:
                    if self.fill_group_select.value != group_value:
                        self.fill_group_select.value = group_value
                finally:
                    self._updating_controls = False

        self._render_plots()

    def _handle_product_change(self, _event) -> None:
        if self._updating_controls:
            return
        self._sync_plot_options(render=True)

    def _handle_plot_change(self, _event) -> None:
        if self._updating_controls:
            return
        self._sync_timestamp_options(render=True)

    def _handle_timestamp_change(self, _event) -> None:
        if self._updating_controls:
            return
        self._render_plots()

    def _handle_fill_group_change(self, _event) -> None:
        if self._updating_controls:
            return
        self._render_plots()

    def _handle_cost_change(self, _event) -> None:
        if self._updating_controls:
            return
        if self._selected_plot_type() in COST_FILTERED_PLOT_TYPES:
            self._render_plots()

    def _handle_simulation_heatmap_setting_change(self, _event) -> None:
        if self._updating_controls:
            return
        group_key = self._selected_simulation_settings_group_key()
        if group_key is None:
            return
        try:
            settings = self._build_settings_from_controls(group_key)
            self._replace_simulation_group_settings(group_key, settings)
            self._save_dashboard_settings()
            self._sync_simulation_heatmap_settings_controls()
            self._render_plots()
        except ValueError as error:
            self._set_status(f"Heatmap settings not saved: {error}", "warning")
            self._sync_simulation_heatmap_settings_controls()

    def _handle_raw_selection_change(self, _event) -> None:
        self._update_raw_summary()

    def _handle_simulation_raw_selection_change(self, _event) -> None:
        self._update_raw_summary()

    def _handle_simulation_select_all(self, _event) -> None:
        self.simulation_raw_select.value = list(self.all_raw_by_label.keys())

    def _handle_simulation_clear_selection(self, _event) -> None:
        self.simulation_raw_select.value = []

    def _handle_simulation_algorithm_change(self, _event) -> None:
        self._sync_simulation_parameter_visibility()

    def _sync_simulation_parameter_visibility(self) -> None:
        self.simulation_time_step_input.visible = (
            self.simulation_algorithm_select.value
            == TIME_AVERAGED_RANDOM_CANCELLATION_NAME
        )

    def _sync_plot_options(self, *, render: bool) -> None:
        product_id = self._selected_product()
        previous_plot_type = self._selected_plot_type()
        plot_options = self._available_plot_labels(product_id) if product_id else []
        plot_select_options = self._with_placeholder_options(
            {plot_label: plot_label for plot_label in plot_options},
            PLOT_PLACEHOLDER,
        )
        previous_plot_label = (
            self._plot_label_for_type(previous_plot_type)
            if previous_plot_type is not None
            else None
        )
        next_plot_label = (
            previous_plot_label if previous_plot_label in plot_options else None
        )

        self._updating_controls = True
        try:
            if self.plot_select.options != plot_select_options:
                self.plot_select.options = plot_select_options
            if self.plot_select.value != next_plot_label:
                self.plot_select.value = next_plot_label
            self._sync_timestamp_options(render=False)
        finally:
            self._updating_controls = False

        if render:
            self._render_plots()

    def _sync_timestamp_options(self, *, render: bool) -> None:
        product_id = self._selected_product()
        plot_type = self._selected_plot_type()
        is_simulation_heatmap = plot_type in SIMULATION_HEATMAP_PLOT_TYPES
        timestamp_options = (
            self._available_timestamp_options(product_id, plot_type)
            if product_id and plot_type and not is_simulation_heatmap
            else {}
        )
        timestamp_select_options = self._with_placeholder_options(
            timestamp_options, TIMESTAMP_PLACEHOLDER
        )
        previous_timestamp = self.timestamp_select.value
        timestamp_values = self._selectable_option_values(timestamp_select_options)
        next_timestamp = (
            previous_timestamp if previous_timestamp in timestamp_values else None
        )

        self._updating_controls = True
        try:
            if self.timestamp_select.visible == is_simulation_heatmap:
                self.timestamp_select.visible = not is_simulation_heatmap
            if self.timestamp_select.disabled != is_simulation_heatmap:
                self.timestamp_select.disabled = is_simulation_heatmap
            if self.timestamp_select.options != timestamp_select_options:
                self.timestamp_select.options = timestamp_select_options
            if self.timestamp_select.value != next_timestamp:
                self.timestamp_select.value = next_timestamp
            self._sync_fill_group_options(render=False)
        finally:
            self._updating_controls = False

        if render:
            self._render_plots()

    def _sync_fill_group_options(self, *, render: bool) -> None:
        product_id = self._selected_product()
        plot_type = self._selected_plot_type()
        is_simulation_heatmap = plot_type in SIMULATION_HEATMAP_PLOT_TYPES
        group_options = (
            self._available_simulation_group_options(product_id)
            if product_id and is_simulation_heatmap
            else {}
        )
        fill_group_select_options = self._with_placeholder_options(
            group_options, FILL_GROUP_PLACEHOLDER
        )
        previous_group = self.fill_group_select.value
        group_values = self._selectable_option_values(fill_group_select_options)
        next_group = previous_group if previous_group in group_values else None

        self._updating_controls = True
        try:
            if self.fill_group_select.visible != is_simulation_heatmap:
                self.fill_group_select.visible = is_simulation_heatmap
            next_disabled = not is_simulation_heatmap
            if self.fill_group_select.disabled != next_disabled:
                self.fill_group_select.disabled = next_disabled
            if self.fill_group_select.options != fill_group_select_options:
                self.fill_group_select.options = fill_group_select_options
            if self.fill_group_select.value != next_group:
                self.fill_group_select.value = next_group
            self._sync_cost_input(render=False)
        finally:
            self._updating_controls = False

        if render:
            self._render_plots()

    def _sync_cost_input(self, *, render: bool) -> None:
        show_cost_input = self._selected_plot_type() in COST_FILTERED_PLOT_TYPES

        self._updating_controls = True
        try:
            if self.cost_input.visible != show_cost_input:
                self.cost_input.visible = show_cost_input
            if self.cost_input.disabled == show_cost_input:
                self.cost_input.disabled = not show_cost_input
        finally:
            self._updating_controls = False

        self._sync_simulation_heatmap_settings_controls()

        if render:
            self._render_plots()

    def _selected_cost(self) -> float:
        raw_value = self.cost_input.value.strip()
        if not raw_value:
            raise ValueError("Cost is required for cost-filtered fill probability plots.")

        try:
            cost = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"Cost must be a finite number: {raw_value!r}") from exc

        if not math.isfinite(cost):
            raise ValueError(f"Cost must be a finite number: {raw_value!r}")

        return cost

    def _build_plot_pane(
        self, plot_type: str, locators: list[PlotDatasetLocator]
    ) -> pn.viewable.Viewable:
        builder = PLOT_REGISTRY[plot_type].plot_builder
        render_options = PlotRenderOptions(
            cost=self._selected_cost() if plot_type in COST_FILTERED_PLOT_TYPES else None,
            simulation_heatmap_settings=(
                self._simulation_heatmap_render_settings()
                if plot_type in SIMULATION_HEATMAP_PLOT_TYPES
                else None
            ),
        )
        plot = builder(locators, render_options=render_options)
        if isinstance(plot, Figure):
            themed_plot = Figure(plot)
            themed_plot.update_layout(**PLOTLY_DARK_LAYOUT)
            plot_height = 1560 if plot_type in SIMULATION_HEATMAP_PLOT_TYPES else 560
            return pn.pane.Plotly(
                themed_plot,
                config={"responsive": True},
                sizing_mode="stretch_width",
                height=plot_height,
                min_height=plot_height,
            )
        return pn.pane.HoloViews(plot, sizing_mode="stretch_both", min_height=560)

    def _available_products(self) -> list[str]:
        return sorted(
            {
                dataset.product_id
                for dataset in self.preprocessed_datasets
                if any(view in PLOT_REGISTRY for view in dataset.available_views)
            }
        )

    def _selected_product(self) -> str | None:
        value = self.product_select.value
        return str(value) if value else None

    def _with_placeholder_options(
        self, options: dict[str, str], placeholder: str
    ) -> dict[str, str | None]:
        return {placeholder: None, **options}

    def _selectable_option_values(self, options) -> set[str]:
        if isinstance(options, dict):
            return {value for value in options.values() if value is not None}
        return {value for value in options if value is not None}

    def _selected_plot_type(self) -> str | None:
        value = self.plot_select.value
        if not value:
            return None
        try:
            return self._plot_type_for_label(str(value))
        except StopIteration:
            return None

    def _plot_label_for_type(self, plot_type: str) -> str:
        return PLOT_LABELS.get(plot_type, plot_type)

    def _plot_type_for_label(self, plot_label: str) -> str:
        return next(key for key, value in PLOT_LABELS.items() if value == plot_label)

    def _datasets_for_product(self, product_id: str) -> list[PreprocessedDataset]:
        return [
            dataset
            for dataset in self.preprocessed_datasets
            if dataset.product_id == product_id
        ]

    def _available_plot_labels(self, product_id: str) -> list[str]:
        plot_types = {
            view
            for dataset in self._datasets_for_product(product_id)
            for view in dataset.available_views
            if view in PLOT_REGISTRY
        }
        return [
            self._plot_label_for_type(plot_type)
            for plot_type in PLOT_REGISTRY
            if plot_type in plot_types
        ]

    def _dataset_selection_key(self, dataset: PreprocessedDataset) -> str:
        return str(dataset.path)

    def _timestamp_option_label(self, dataset: PreprocessedDataset) -> str:
        formatted_timestamp = parse_timestamp(dataset.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return f"{formatted_timestamp} | {format_time_step(dataset.time_step)}s"

    def _available_timestamp_options(
        self, product_id: str, plot_type: str
    ) -> dict[str, str]:
        datasets_by_key: dict[str, PreprocessedDataset] = {}
        for dataset in self._datasets_for_product(product_id):
            if plot_type not in dataset.available_views:
                continue
            datasets_by_key.setdefault(self._dataset_selection_key(dataset), dataset)

        label_counts: dict[str, int] = {}
        options: dict[str, str] = {}
        for dataset in sorted(
            datasets_by_key.values(),
            key=lambda item: (item.timestamp, item.time_step, item.path.name),
        ):
            base_label = self._timestamp_option_label(dataset)
            label_counts[base_label] = label_counts.get(base_label, 0) + 1
            label = base_label
            if label_counts[base_label] > 1:
                label = f"{base_label} | {dataset.path.name}"
            options[label] = self._dataset_selection_key(dataset)
        return options

    def _simulation_group_value(
        self, group_key: tuple[str, float, str | None, str]
    ) -> str:
        product_id, time_step, time_step_token, signature = group_key
        token = time_step_token or format_time_step(time_step)
        return "|".join((product_id, token, signature))

    def _simulation_group_label(
        self,
        group_key: tuple[str, float, str | None, str],
        group: list[PreprocessedDataset],
    ) -> str:
        _product_id, time_step, time_step_token, signature = group_key
        token = time_step_token or format_time_step(time_step)
        timestamp_count = len({dataset.timestamp for dataset in group})
        simulation_count = len(
            {
                dataset.simulation_path
                for dataset in group
                if dataset.simulation_path is not None
            }
        )
        return (
            f"{format_time_step(time_step)}s ({token}) | {signature} | "
            f"{timestamp_count} timestamp(s), {simulation_count} simulation file(s)"
        )

    def _available_simulation_group_options(self, product_id: str) -> dict[str, str]:
        simulation_datasets = [
            dataset
            for dataset in self._datasets_for_product(product_id)
            if any(
                view in dataset.available_views
                for view in SIMULATION_HEATMAP_PLOT_TYPES
            )
            and dataset.simulation_path is not None
        ]
        groups = self._simulation_groups(simulation_datasets)
        return {
            self._simulation_group_label(group_key, group): self._simulation_group_value(
                group_key
            )
            for group_key, group in sorted(groups.items())
        }

    def _simulation_parameter_signature(self, dataset: PreprocessedDataset) -> str:
        if dataset.simulation_path is None:
            return "simulation-parameters-unrecognized"
        file_name = dataset.simulation_path.name
        if dataset.timestamp not in file_name:
            return "simulation-parameters-unrecognized"
        signature = file_name.replace(dataset.timestamp, "")
        return signature.strip("-_. ") or "simulation-parameters-unrecognized"

    def _simulation_group_key(
        self, dataset: PreprocessedDataset
    ) -> tuple[str, float, str | None, str]:
        return (
            dataset.product_id,
            dataset.time_step,
            dataset.time_step_token,
            self._simulation_parameter_signature(dataset),
        )

    def _simulation_groups(
        self, datasets: list[PreprocessedDataset]
    ) -> dict[tuple[str, float, str | None, str], list[PreprocessedDataset]]:
        groups: dict[tuple[str, float, str | None, str], list[PreprocessedDataset]] = {}
        for dataset in datasets:
            groups.setdefault(self._simulation_group_key(dataset), []).append(
                dataset
            )
        return {
            key: sorted(group, key=lambda dataset: dataset.timestamp)
            for key, group in groups.items()
        }

    def _selected_datasets_for_plot(self) -> list[PreprocessedDataset]:
        product_id = self._selected_product()
        plot_type = self._selected_plot_type()
        if product_id is None or plot_type is None:
            return []

        product_datasets = self._datasets_for_product(product_id)
        if plot_type in SIMULATION_HEATMAP_PLOT_TYPES:
            selected_group = self.fill_group_select.value
            if not selected_group:
                return []
            selected_datasets = [
                dataset
                for dataset in product_datasets
                if plot_type in dataset.available_views
                and dataset.simulation_path is not None
                and self._simulation_group_value(self._simulation_group_key(dataset))
                == selected_group
            ]
            return sorted(selected_datasets, key=lambda dataset: dataset.timestamp)

        selected_dataset_key = self.timestamp_select.value
        if not selected_dataset_key:
            return []

        matching_datasets = [
            dataset
            for dataset in product_datasets
            if self._dataset_selection_key(dataset) == selected_dataset_key
            and plot_type in dataset.available_views
        ]
        non_simulation_datasets = [
            dataset for dataset in matching_datasets if dataset.simulation_path is None
        ]
        if non_simulation_datasets:
            return [non_simulation_datasets[0]]
        return matching_datasets[:1]

    def _update_dataset_summary(self) -> None:
        if not self.preprocessed_datasets:
            self.dataset_summary.object = (
                "**Current product:** None\n\n"
                "No preprocessed datasets were found. Run preprocessing on a raw "
                "batch or refresh the catalog after adding `.npz` files."
            )
            return

        product_id = self._selected_product()
        plot_type = self._selected_plot_type()
        plot_label = self._plot_label_for_type(plot_type) if plot_type else "None"
        if product_id is None:
            self.dataset_summary.object = (
                "**Current product:** None\n\n"
                "No product with plottable preprocessed data is available."
            )
            return

        product_datasets = self._datasets_for_product(product_id)
        available_views = [
            self._plot_label_for_type(plot_type)
            for plot_type in PLOT_REGISTRY
            if any(plot_type in dataset.available_views for dataset in product_datasets)
        ]
        selected_datasets = self._selected_datasets_for_plot()

        if plot_type in SIMULATION_HEATMAP_PLOT_TYPES:
            groups = self._simulation_groups(selected_datasets)
            group_lines = []
            for (
                _product,
                time_step,
                time_step_token,
                signature,
            ), group in groups.items():
                timestamp_count = len({dataset.timestamp for dataset in group})
                simulation_count = len(
                    {
                        dataset.simulation_path
                        for dataset in group
                        if dataset.simulation_path is not None
                    }
                )
                group_lines.append(
                    f"- `{format_time_step(time_step)}s` "
                    f"(`{time_step_token or format_time_step(time_step)}`) / "
                    f"`{signature}`: {timestamp_count} timestamp(s), "
                    f"{simulation_count} simulation file(s)"
                )
            group_summary = "\n".join(group_lines) or "- None"
            self.dataset_summary.object = (
                f"**Current product:** {product_id}\n\n"
                f"**Current plot:** {plot_label}\n\n"
                f"**Merged timestamp count:** "
                f"{len({dataset.timestamp for dataset in selected_datasets})}\n\n"
                f"**Simulation file count:** "
                f"{len({dataset.simulation_path for dataset in selected_datasets if dataset.simulation_path is not None})}\n\n"
                f"**Time step / parameter groups**\n{group_summary}\n\n"
                f"**Available views:** {', '.join(available_views) or 'None'}"
            )
            return

        selected_dataset = selected_datasets[0] if selected_datasets else None
        formatted_timestamp = (
            parse_timestamp(selected_dataset.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if selected_dataset is not None
            else "None"
        )
        selected_time_step = (
            f"{format_time_step(selected_dataset.time_step)}s"
            if selected_dataset is not None
            else "None"
        )
        self.dataset_summary.object = (
            f"**Current product:** {product_id}\n\n"
            f"**Current plot:** {plot_label}\n\n"
            f"**Selected timestamp:** {formatted_timestamp}\n\n"
            f"**Selected time step:** {selected_time_step}\n\n"
            f"**Matching dataset count:** {len(selected_datasets)}\n\n"
            f"**Available views:** {', '.join(available_views) or 'None'}"
        )

    def _update_raw_summary(self) -> None:
        pending_count = len(self.raw_by_label)
        preprocess_selected_count = len(
            [label for label in self.raw_select.value if label in self.raw_by_label]
        )
        discovered_count = len(self.all_raw_by_label)
        simulation_selected_count = len(
            [
                label
                for label in self.simulation_raw_select.value
                if label in self.all_raw_by_label
            ]
        )
        if pending_count == 0 and discovered_count == 0:
            self.raw_summary.object = (
                f"**Raw data directory:** `{self.raw_dir}`\n\n"
                "**Pending raw batch count:** 0\n\n"
                "**Selected preprocess batch count:** 0\n\n"
                "**Discovered raw batch count:** 0\n\n"
                "**Selected simulation batch count:** 0\n\n"
                "No raw batches are available."
            )
            return

        self.raw_summary.object = (
            f"**Raw data directory:** `{self.raw_dir}`\n\n"
            f"**Pending raw batch count:** {pending_count}\n\n"
            f"**Selected preprocess batch count:** {preprocess_selected_count}\n\n"
            f"**Discovered raw batch count:** {discovered_count}\n\n"
            f"**Selected simulation batch count:** {simulation_selected_count}"
        )

    def _select_fill_probability_dataset(self, dataset: PreprocessedDataset) -> None:
        if (
            dataset.product_id not in self._selectable_option_values(self.product_select.options)
            or dataset.simulation_path is None
        ):
            return

        fill_probability_label = self._plot_label_for_type("fill_probability")
        self._updating_controls = True
        try:
            if self.product_select.value != dataset.product_id:
                self.product_select.value = dataset.product_id
        finally:
            self._updating_controls = False

        self._sync_plot_options(render=False)
        if fill_probability_label in self.plot_select.options:
            self._updating_controls = True
            try:
                if self.plot_select.value != fill_probability_label:
                    self.plot_select.value = fill_probability_label
            finally:
                self._updating_controls = False
            self._sync_timestamp_options(render=False)

        group_value = self._simulation_group_value(
            self._simulation_group_key(dataset)
        )
        if group_value in set(self.fill_group_select.options.values()):
            self._updating_controls = True
            try:
                if self.fill_group_select.value != group_value:
                    self.fill_group_select.value = group_value
            finally:
                self._updating_controls = False

        self._render_plots()

    def _format_timestamp_range(self, timestamps: list[str]) -> str:
        if not timestamps:
            return "None"
        first = parse_timestamp(timestamps[0]).strftime("%Y-%m-%d %H:%M:%S")
        last = parse_timestamp(timestamps[-1]).strftime("%Y-%m-%d %H:%M:%S")
        if first == last:
            return first
        return f"{first} → {last}"

    def _empty_state(self, message: str, level: str = "info") -> pn.pane.Alert:
        return pn.pane.Alert(message, alert_type=level, sizing_mode="stretch_width")

    def _render_error_alert(
        self, plot_label: str, error: Exception | None = None
    ) -> pn.pane.Alert:
        if error is None:
            return pn.pane.Alert(
                f"No render errors for {plot_label}.",
                alert_type="danger",
                sizing_mode="stretch_width",
                visible=False,
            )

        return pn.pane.Alert(
            f"Failed to render {plot_label}.\n\n"
            f"**Technical details**\n\n```text\n{error}\n```",
            alert_type="danger",
            sizing_mode="stretch_width",
        )

    def _plot_card(
        self,
        plot_type: str,
        plot_label: str,
        selected_dataset_count: int,
        result_pane: pn.viewable.Viewable,
        *,
        error: Exception | None = None,
        notice: pn.viewable.Viewable | None = None,
        css_classes: list[str] | None = None,
    ) -> pn.Card:
        metadata = pn.pane.Markdown(
            f"**Plot:** {plot_label}  \n"
            f"**Selected dataset count:** {selected_dataset_count}",
            sizing_mode="stretch_width",
            margin=(0, 0, 10, 0),
        )
        result_classes = ["qf-plot-result"]
        card_classes = ["qf-main-plot-card", *(css_classes or [])]
        if plot_type in SIMULATION_HEATMAP_PLOT_TYPES:
            result_classes.append("qf-fill-probability-result")
            card_classes.append("qf-fill-probability-card")
        result_container = pn.Column(
            result_pane,
            sizing_mode="stretch_both",
            css_classes=result_classes,
            margin=(0, 0, 12, 0),
        )
        objects = [metadata]
        if notice is not None:
            objects.append(notice)
        objects.extend([result_container, self._render_error_alert(plot_label, error)])
        return self._card(
            *objects,
            title=plot_label,
            sizing_mode="stretch_both",
            css_classes=card_classes,
            margin=(0, 0, 0, 0),
        )

    def _unsupported_plot_card(
        self,
        plot_label: str,
        plot_type: str,
        selected_datasets: list[PreprocessedDataset],
    ) -> pn.Card:
        unsupported = [
            dataset.display_name
            for dataset in selected_datasets
            if plot_type not in dataset.available_views
        ]
        dataset_lines = "\n".join(f"- `{dataset}`" for dataset in unsupported)
        notice = pn.pane.Alert(
            f"{plot_label} is unavailable for {len(unsupported)} selected "
            "dataset(s). Deselect unsupported datasets or choose another plot.",
            alert_type="warning",
            sizing_mode="stretch_width",
        )
        details = pn.pane.Markdown(
            "No render result is available for this plot with the current "
            f"dataset selection.\n\n**Unsupported datasets**\n{dataset_lines}",
            sizing_mode="stretch_width",
        )
        return self._plot_card(
            plot_type,
            plot_label,
            len(selected_datasets),
            details,
            notice=notice,
            css_classes=["qf-warning-card"],
        )

    def _render_error_card(
        self, plot_label: str, selected_dataset_count: int, error: Exception
    ) -> pn.Card:
        result_placeholder = pn.pane.Markdown(
            "Render output is unavailable because the plot builder raised an "
            "exception. See the render error alert below for details.",
            sizing_mode="stretch_width",
        )
        return self._plot_card(
            "unknown",
            plot_label,
            selected_dataset_count,
            result_placeholder,
            error=error,
        )

    def _plot_selection_empty_state(self) -> pn.pane.Alert | None:
        if not self.preprocessed_datasets:
            return self._empty_state(
                "No preprocessed datasets were found. Preprocess a raw batch or "
                "refresh the catalog after adding `.npz` files.",
                "warning",
            )

        product_id = self._selected_product()
        if product_id is None:
            if self._selectable_option_values(self.product_select.options):
                return self._empty_state("Select a product to start plotting.", "info")
            return self._empty_state(
                "No product has plottable preprocessed data. Refresh the catalog "
                "after adding datasets with available views.",
                "info",
            )

        plot_type = self._selected_plot_type()
        if plot_type is None:
            if self._selectable_option_values(self.plot_select.options):
                return self._empty_state(
                    f"Select a plot for `{product_id}` to start rendering.",
                    "info",
                )
            return self._empty_state(
                f"Selected product `{product_id}` does not have any available plots.",
                "warning",
            )

        if plot_type in SIMULATION_HEATMAP_PLOT_TYPES:
            if not self._selectable_option_values(self.fill_group_select.options):
                plot_label = self._plot_label_for_type(plot_type)
                return self._empty_state(
                    f"{plot_label} cannot be rendered because no mergeable "
                    f"simulation datasets were found for `{product_id}`.",
                    "warning",
                )
            if not self.fill_group_select.value:
                return self._empty_state(
                    f"Select a simulation group for `{product_id}` before rendering.",
                    "info",
                )
            return None

        if not self.timestamp_select.value:
            if not self._selectable_option_values(self.timestamp_select.options):
                return self._empty_state(
                    f"Selected plot `{self._plot_label_for_type(plot_type)}` does not "
                    f"have any plottable timestamps for `{product_id}`.",
                    "warning",
                )
            return self._empty_state(
                f"Select a timestamp for `{self._plot_label_for_type(plot_type)}` "
                f"under `{product_id}` before rendering.",
                "info",
            )

        if not self._selected_datasets_for_plot():
            return self._empty_state(
                "No dataset matches the selected product, plot, and timestamp.",
                "warning",
            )

        return None

    def _render_plots(self) -> None:
        self._update_dataset_summary()

        empty_state = self._plot_selection_empty_state()
        if empty_state is not None:
            self.plot_area.objects = [empty_state]
            return

        plot_type = self._selected_plot_type()
        if plot_type is None:
            self.plot_area.objects = [
                self._empty_state("Select a plot type before rendering.", "warning")
            ]
            return
        plot_label = self._plot_label_for_type(plot_type)
        selected_datasets = self._selected_datasets_for_plot()
        locators: list[PlotDatasetLocator] = [
            dataset.to_locator(self.preprocessed_dir) for dataset in selected_datasets
        ]
        selected_dataset_count = len(selected_datasets)

        try:
            result_pane = self._build_plot_pane(plot_type, locators)
            self.plot_area.objects = [
                self._plot_card(
                    plot_type, plot_label, selected_dataset_count, result_pane
                )
            ]
        except Exception as error:
            self.plot_area.objects = [
                self._render_error_card(plot_label, selected_dataset_count, error)
            ]

    def _card(
        self,
        *objects,
        title: str,
        css_classes: list[str] | None = None,
        sizing_mode: str = "stretch_width",
        margin: tuple[int, int, int, int] = (0, 0, 18, 0),
    ) -> pn.Card:
        classes = ["qf-card", *(css_classes or [])]
        return pn.Card(
            *objects,
            title=title,
            collapsed=False,
            sizing_mode=sizing_mode,
            margin=margin,
            css_classes=classes,
        )

    def _section_heading(self, title: str, subtitle: str) -> pn.Column:
        return pn.Column(
            pn.pane.Markdown(
                f"## {title}", css_classes=["qf-section-title"], margin=(0, 0, 2, 0)
            ),
            pn.pane.Markdown(
                subtitle, css_classes=["qf-section-subtitle"], margin=(0, 0, 12, 0)
            ),
            sizing_mode="stretch_width",
        )

    def build_header(self) -> pn.Row:
        title = pn.Column(
            pn.pane.HTML(
                '<p class="qf-eyebrow">Market microstructure console</p>', margin=0
            ),
            pn.pane.Markdown(
                "# Orderbook Dashboard", css_classes=["qf-title"], margin=(0, 0, 4, 0)
            ),
            pn.pane.Markdown(
                "Coinbase market data catalog, preprocessing, and interactive order book visualizations.",
                css_classes=["qf-section-subtitle"],
                margin=0,
            ),
            sizing_mode="stretch_width",
            margin=(0, 20, 0, 0),
        )
        actions = pn.Row(
            self.refresh_button,
            sizing_mode="stretch_width",
            align="center",
            css_classes=["qf-button-row"],
        )
        return pn.Row(
            title,
            pn.Spacer(sizing_mode="stretch_width"),
            actions,
            sizing_mode="stretch_width",
            align="center",
            css_classes=["qf-dashboard-header", "qf-responsive-row"],
            margin=(0, 0, 20, 0),
        )

    def build_dataset_section(self) -> pn.Card:
        return self._card(
            self.product_select,
            self.raw_dir_input,
            self.apply_raw_dir_button,
            self.dataset_summary,
            title="Dataset selection",
        )

    def build_sidebar(self) -> pn.Column:
        raw_batch_section = self._card(
            self.raw_select,
            self.raw_summary,
            pn.Row(
                self.preprocess_button,
                self.preprocess_spinner,
                sizing_mode="stretch_width",
                align="center",
                css_classes=["qf-button-row"],
            ),
            self.preprocess_progress,
            title="Raw batch preprocessing",
        )
        simulation_section = self._card(
            self.simulation_raw_select,
            pn.Row(
                self.simulation_select_all_button,
                self.simulation_clear_selection_button,
                sizing_mode="stretch_width",
                align="center",
                css_classes=["qf-button-row"],
            ),
            self.simulation_algorithm_select,
            self.simulation_resolved_time_input,
            self.simulation_time_step_input,
            pn.Row(
                self.simulation_button,
                self.simulation_spinner,
                sizing_mode="stretch_width",
                align="center",
                css_classes=["qf-button-row"],
            ),
            self.simulation_progress,
            title="Virtual order simulation",
        )
        return pn.Column(
            self._section_heading(
                "Controls",
                "Choose datasets, preprocess raw batches, run simulations, and refresh the catalog.",
            ),
            self.build_dataset_section(),
            raw_batch_section,
            simulation_section,
            sizing_mode="stretch_width",
            min_width=300,
            max_width=420,
            margin=(8, 6, 8, 6),
        )

    def build_plot_section(self) -> pn.Column:
        is_simulation_heatmap = (
            self._selected_plot_type() in SIMULATION_HEATMAP_PLOT_TYPES
        )
        show_cost_input = self._selected_plot_type() in COST_FILTERED_PLOT_TYPES
        self.timestamp_select.visible = not is_simulation_heatmap
        self.timestamp_select.disabled = is_simulation_heatmap
        self.fill_group_select.visible = is_simulation_heatmap
        self.fill_group_select.disabled = not is_simulation_heatmap
        self.cost_input.visible = show_cost_input
        self.cost_input.disabled = not show_cost_input
        self._sync_simulation_heatmap_settings_controls()
        plot_controls = self._card(
            self.plot_select,
            self.timestamp_select,
            self.fill_group_select,
            self.cost_input,
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
            title="Plot controls",
            css_classes=["qf-plot-controls"],
        )
        workspace = self._card(
            self.plot_area,
            title="Plot workspace",
            sizing_mode="stretch_both",
            css_classes=["qf-plot-workspace"],
            margin=(0, 0, 0, 0),
        )
        return pn.Column(
            self._section_heading(
                "Visualization",
                "Inspect order book depth and companion Plotly analytics in one workspace.",
            ),
            plot_controls,
            workspace,
            sizing_mode="stretch_both",
            min_width=760,
        )

    def build_status_section(self) -> pn.Card:
        return self._card(
            self.status,
            title="Status",
            css_classes=["qf-status-card"],
        )

    def view(self):
        return pn.template.FastListTemplate(
            title="Orderbook Viewer",
            sidebar=[self.build_sidebar()],
            main=[
                self.build_header(),
                self.build_plot_section(),
                self.build_status_section(),
            ],
            theme="dark",
            accent_base_color="#22d3ee",
            header_background="#020617",
            header_color="#f8fafc",
            background_color="#020617",
            neutral_color="#1e293b",
            sidebar_width=420,
            main_max_width="1440px",
            main_layout=None,
        )


def build_app():
    hv.extension("bokeh")
    pn.extension("plotly", raw_css=[DASHBOARD_CSS])
    dashboard = OrderbookDashboard(RAW_DATA_DIR, PREPROCESSED_DIR)
    return dashboard.view()


def main() -> None:
    pn.serve(build_app, title="Orderbook Viewer", show=True)


if __name__ == "__main__":
    main()

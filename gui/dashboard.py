"""Orderbook dashboard composition root that wires widgets, state, and mixins."""

from __future__ import annotations

from pathlib import Path

import panel as pn

from src.preprocess import PreprocessedDataset, RawBatch
from src.simulation import (
    DEFAULT_RESOLVED_TIME,
    DEFAULT_TIME_STEP as DEFAULT_SIMULATION_TIME_STEP,
    list_algorithms,
)

from .actions import DashboardActionsMixin
from .catalog import DashboardCatalogMixin
from .layout import DashboardLayoutMixin
from .rendering import DashboardRenderingMixin
from .simulation_controls import SimulationControlsMixin


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_SETTINGS_PATH = DEFAULT_PROJECT_ROOT / "gui" / "dashboard_settings.json"


class OrderbookDashboard(
    DashboardCatalogMixin,
    SimulationControlsMixin,
    DashboardActionsMixin,
    DashboardRenderingMixin,
    DashboardLayoutMixin,
):
    """Interactive Panel dashboard for cataloging, preprocessing, and plotting data."""

    PRODUCT_PLACEHOLDER = "Select a product..."

    def __init__(
        self,
        raw_dir: Path,
        preprocessed_dir: Path,
        settings_path: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        """Initialize dashboard state, widgets, and event wiring."""
        self.project_root = project_root or DEFAULT_PROJECT_ROOT
        self.raw_dir = raw_dir
        self.preprocessed_dir = preprocessed_dir
        self.dashboard_settings_path = settings_path or DEFAULT_DASHBOARD_SETTINGS_PATH
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
        algorithm_names = list_algorithms()
        self.simulation_algorithm_select = pn.widgets.Select(
            name="Simulation algorithm",
            options=algorithm_names,
            value=(algorithm_names[0] if algorithm_names else None),
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

    def _resolve_raw_dir(self, raw_dir_value: str) -> Path:
        """Resolve a user-supplied raw directory path relative to the project root."""
        candidate = Path(raw_dir_value.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = (self.project_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            raise ValueError(f"Raw data directory does not exist: {candidate}")
        if not candidate.is_dir():
            raise ValueError(f"Raw data directory is not a directory: {candidate}")
        return candidate

    def _display_raw_dir(self, raw_dir: Path) -> str:
        """Format a raw directory path for display in the text input."""
        try:
            return str(raw_dir.resolve().relative_to(self.project_root))
        except ValueError:
            return str(raw_dir.resolve())

    def _set_status(self, message: str, level: str = "light") -> None:
        """Update the status alert message and alert type."""
        self.status.object = message
        self.status.alert_type = level

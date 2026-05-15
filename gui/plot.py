from __future__ import annotations

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import holoviews as hv
import panel as pn
from plotly.graph_objects import Figure

from gui.data_catalog import (
    PlotDatasetLocator,
    PreprocessedDataset,
    discover_preprocessed_datasets,
    discover_raw_batches,
    format_time_step,
    parse_timestamp,
)
from gui.registry import PLOT_LABELS, PLOT_REGISTRY
from gui.preprocess_service import preprocess_batches

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"

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
}
"""

PLOTLY_DARK_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(2, 6, 23, 0)",
    "plot_bgcolor": "rgba(15, 23, 42, 0.92)",
    "font": {"color": "#e5eefb"},
    "margin": {"l": 56, "r": 32, "t": 54, "b": 48},
}


class OrderbookDashboard:
    def __init__(self, raw_dir: Path, preprocessed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.preprocessed_dir = preprocessed_dir
        self.preprocessed_by_label: dict[str, PreprocessedDataset] = {}
        self.raw_by_label = {}
        self.status = pn.pane.Alert(
            "Ready.", alert_type="light", sizing_mode="stretch_width"
        )
        self.preprocessed_select = pn.widgets.MultiChoice(
            name="Preprocessed datasets",
            options=[],
            sizing_mode="stretch_width",
            min_height=180,
        )
        self.raw_select = pn.widgets.MultiChoice(
            name="Raw batches pending preprocess",
            options=[],
            sizing_mode="stretch_width",
            min_height=180,
        )
        self.plot_select = pn.widgets.MultiChoice(
            name="Plots",
            value=[],
            options=list(PLOT_LABELS.values()),
            sizing_mode="stretch_width",
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
        self.plot_area = pn.Column(
            pn.pane.Markdown(
                "Select one or more preprocessed datasets to start plotting."
            ),
            sizing_mode="stretch_both",
            min_width=720,
        )

        self.refresh_button.on_click(self._handle_refresh)
        self.preprocess_button.on_click(self._handle_preprocess)
        self.preprocessed_select.param.watch(self._handle_selection_change, "value")
        self.raw_select.param.watch(self._handle_raw_selection_change, "value")
        self.plot_select.param.watch(self._handle_selection_change, "value")

        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        datasets = discover_preprocessed_datasets(self.preprocessed_dir)
        batches = discover_raw_batches(self.raw_dir, self.preprocessed_dir)
        self.preprocessed_by_label = {
            dataset.display_name: dataset for dataset in datasets
        }
        self.raw_by_label = {
            batch.display_name: batch for batch in batches if not batch.is_preprocessed
        }

        existing_preprocessed = [
            label
            for label in self.preprocessed_select.value
            if label in self.preprocessed_by_label
        ]
        existing_raw = [
            label for label in self.raw_select.value if label in self.raw_by_label
        ]

        self.preprocessed_select.options = list(self.preprocessed_by_label.keys())
        self.preprocessed_select.value = existing_preprocessed

        self.raw_select.options = list(self.raw_by_label.keys())
        self.raw_select.value = existing_raw

        self._update_raw_summary()
        self._render_plots()

    def _set_status(self, message: str, level: str = "light") -> None:
        self.status.object = message
        self.status.alert_type = level

    def _handle_refresh(self, _event) -> None:
        self.refresh_catalog()
        self._set_status("Catalog refreshed.", "success")

    def _set_preprocess_loading(self, is_loading: bool) -> None:
        self.preprocess_button.disabled = is_loading
        self.preprocess_button.loading = is_loading
        self.preprocess_spinner.value = is_loading
        self.preprocess_spinner.visible = is_loading
        self.preprocess_progress.loading = is_loading

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
        progress_messages = [
            f"Queued {batch_count} raw batch(es) for preprocessing."
        ]
        self.preprocess_progress.object = self._format_preprocess_progress(
            batch_count, progress_messages
        )
        self._set_status(
            f"Preprocessing {batch_count} raw batch(es)...", "primary"
        )
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
            new_labels = sorted(
                dataset.display_name
                for dataset in preprocessed_datasets
                if dataset.display_name in self.preprocessed_by_label
            )
            if new_labels:
                self.preprocessed_select.value = new_labels
            summary = (
                f"Completed preprocessing {batch_count} batch(es). "
                f"Generated {len(new_labels)} preprocessed dataset(s)."
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

    def _handle_selection_change(self, _event) -> None:
        self._render_plots()

    def _handle_raw_selection_change(self, _event) -> None:
        self._update_raw_summary()

    def _build_plot_pane(
        self, plot_type: str, locators: list[PlotDatasetLocator]
    ) -> pn.viewable.Viewable:
        builder = PLOT_REGISTRY[plot_type].plot_builder
        plot = builder(locators)
        if isinstance(plot, Figure):
            themed_plot = Figure(plot)
            themed_plot.update_layout(**PLOTLY_DARK_LAYOUT)
            return pn.pane.Plotly(
                themed_plot,
                config={"responsive": True},
                sizing_mode="stretch_both",
                min_height=560,
            )
        return pn.pane.HoloViews(
            plot, sizing_mode="stretch_both", min_height=560
        )

    def _selected_datasets(self) -> list[PreprocessedDataset]:
        return [
            self.preprocessed_by_label[label]
            for label in self.preprocessed_select.value
            if label in self.preprocessed_by_label
        ]

    def _selected_plot_labels(self) -> list[str]:
        return [
            label for label in self.plot_select.value if label in PLOT_LABELS.values()
        ]

    def _update_dataset_summary(
        self, selected_datasets: list[PreprocessedDataset]
    ) -> None:
        if not self.preprocessed_by_label:
            self.dataset_summary.object = (
                "**Selected dataset count:** 0\n\n"
                "No preprocessed datasets were found. Run preprocessing on a raw "
                "batch or refresh the catalog after adding `.npz` files."
            )
            return

        if not selected_datasets:
            self.dataset_summary.object = (
                "**Selected dataset count:** 0\n\n"
                "Choose one or more preprocessed datasets to see product, time, "
                "step, and view details."
            )
            return

        product_ids = sorted({dataset.product_id for dataset in selected_datasets})
        timestamps = sorted(dataset.timestamp for dataset in selected_datasets)
        time_steps = sorted(
            {format_time_step(dataset.time_step) for dataset in selected_datasets}
        )
        available_views = sorted(
            {
                PLOT_LABELS.get(view, view)
                for dataset in selected_datasets
                for view in dataset.available_views
            }
        )
        timestamp_range = self._format_timestamp_range(timestamps)
        dataset_lines = "\n".join(
            f"- `{dataset.display_name}`" for dataset in selected_datasets
        )
        self.dataset_summary.object = (
            f"**Selected dataset count:** {len(selected_datasets)}\n\n"
            f"**Product id:** {', '.join(product_ids)}\n\n"
            f"**Timestamp range:** {timestamp_range}\n\n"
            f"**Time step:** {', '.join(f'{step}s' for step in time_steps)}\n\n"
            f"**Available views:** {', '.join(available_views) or 'None'}\n\n"
            f"**Datasets**\n{dataset_lines}"
        )

    def _update_raw_summary(self) -> None:
        pending_count = len(self.raw_by_label)
        selected_count = len(
            [label for label in self.raw_select.value if label in self.raw_by_label]
        )
        if pending_count == 0:
            self.raw_summary.object = (
                "**Pending raw batch count:** 0\n\n"
                "**Selected raw batch count:** 0\n\n"
                "No raw batches are ready for preprocessing."
            )
            return

        self.raw_summary.object = (
            f"**Pending raw batch count:** {pending_count}\n\n"
            f"**Selected raw batch count:** {selected_count}"
        )

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
        result_container = pn.Column(
            result_pane,
            sizing_mode="stretch_both",
            css_classes=["qf-plot-result"],
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
            css_classes=["qf-main-plot-card", *(css_classes or [])],
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
            plot_label, selected_dataset_count, result_placeholder, error=error
        )

    def _plot_selection_empty_state(
        self,
        selected_datasets: list[PreprocessedDataset],
        selected_plot_labels: list[str],
    ) -> pn.pane.Alert | None:
        if not self.preprocessed_by_label:
            return self._empty_state(
                "No preprocessed datasets were found. Preprocess a raw batch or "
                "refresh the catalog after adding `.npz` files.",
                "warning",
            )

        if not selected_datasets:
            return self._empty_state(
                "Select one or more preprocessed datasets to start plotting.",
                "info",
            )

        if not selected_plot_labels:
            return self._empty_state("Select at least one plot type.", "warning")

        product_ids = sorted({dataset.product_id for dataset in selected_datasets})
        if len(product_ids) != 1:
            return self._empty_state(
                "Datasets must share a single product before plotting. "
                f"Selected products: {', '.join(product_ids)}. "
                "Deselect datasets until only one product remains.",
                "warning",
            )

        return None

    def _plot_type_for_label(self, plot_label: str) -> str:
        return next(key for key, value in PLOT_LABELS.items() if value == plot_label)

    def _render_plots(self) -> None:
        selected_datasets = self._selected_datasets()
        selected_plot_labels = self._selected_plot_labels()
        self._update_dataset_summary(selected_datasets)

        empty_state = self._plot_selection_empty_state(
            selected_datasets, selected_plot_labels
        )
        if empty_state is not None:
            self.plot_area.objects = [empty_state]
            return

        locators: list[PlotDatasetLocator] = [
            dataset.to_locator(self.preprocessed_dir) for dataset in selected_datasets
        ]
        plot_cards: list[pn.Card] = []
        selected_dataset_count = len(selected_datasets)

        for plot_label in selected_plot_labels:
            plot_type = self._plot_type_for_label(plot_label)
            if any(
                plot_type not in dataset.available_views
                for dataset in selected_datasets
            ):
                plot_cards.append(
                    self._unsupported_plot_card(
                        plot_label, plot_type, selected_datasets
                    )
                )
                continue

            try:
                result_pane = self._build_plot_pane(plot_type, locators)
                plot_cards.append(
                    self._plot_card(
                        plot_label, selected_dataset_count, result_pane
                    )
                )
            except Exception as error:
                plot_cards.append(
                    self._render_error_card(
                        plot_label, selected_dataset_count, error
                    )
                )

        if not plot_cards:
            self.plot_area.objects = [
                self._empty_state("No plots are available for the current selection.")
            ]
            return

        if len(plot_cards) == 1:
            self.plot_area.objects = plot_cards
            return

        self.plot_area.objects = [
            pn.Tabs(
                *[(card.title, card) for card in plot_cards],
                sizing_mode="stretch_both",
                dynamic=True,
                css_classes=["qf-plot-tabs"],
            )
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
            self.preprocessed_select,
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
        return pn.Column(
            self._section_heading(
                "Controls",
                "Choose datasets, preprocess raw batches, and refresh the catalog.",
            ),
            self.build_dataset_section(),
            raw_batch_section,
            sizing_mode="stretch_width",
            min_width=300,
            max_width=420,
            margin=(8, 6, 8, 6),
        )

    def build_plot_section(self) -> pn.Column:
        plot_controls = self._card(
            self.plot_select,
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

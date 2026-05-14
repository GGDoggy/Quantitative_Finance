from __future__ import annotations

from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import holoviews as hv
import panel as pn
from plotly.graph_objects import Figure

from gui.data_catalog import PlotDatasetLocator, discover_preprocessed_datasets, discover_raw_batches
from gui.registry import PLOT_LABELS, PLOT_REGISTRY
from gui.preprocess_service import preprocess_batches


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"


class OrderbookDashboard:
    def __init__(self, raw_dir: Path, preprocessed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.preprocessed_dir = preprocessed_dir
        self.preprocessed_by_label = {}
        self.raw_by_label = {}
        self.status = pn.pane.Alert("Ready.", alert_type="light", sizing_mode="stretch_width")
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
            value=["Orderbook"],
            options=list(PLOT_LABELS.values()),
            sizing_mode="stretch_width",
        )
        self.refresh_button = pn.widgets.Button(name="Refresh Catalog", button_type="default", sizing_mode="stretch_width")
        self.preprocess_button = pn.widgets.Button(name="Preprocess Selected", button_type="primary", sizing_mode="stretch_width")
        self.plot_area = pn.Column(
            pn.pane.Markdown("Select one or more preprocessed datasets to start plotting."),
            sizing_mode="stretch_both",
        )

        self.refresh_button.on_click(self._handle_refresh)
        self.preprocess_button.on_click(self._handle_preprocess)
        self.preprocessed_select.param.watch(self._handle_selection_change, "value")
        self.plot_select.param.watch(self._handle_selection_change, "value")

        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        datasets = discover_preprocessed_datasets(self.preprocessed_dir)
        batches = discover_raw_batches(self.raw_dir, self.preprocessed_dir)
        self.preprocessed_by_label = {dataset.display_name: dataset for dataset in datasets}
        self.raw_by_label = {
            batch.display_name: batch
            for batch in batches
            if not batch.is_preprocessed
        }

        existing_preprocessed = [label for label in self.preprocessed_select.value if label in self.preprocessed_by_label]
        existing_raw = [label for label in self.raw_select.value if label in self.raw_by_label]

        self.preprocessed_select.options = list(self.preprocessed_by_label.keys())
        self.preprocessed_select.value = existing_preprocessed

        self.raw_select.options = list(self.raw_by_label.keys())
        self.raw_select.value = existing_raw

        if not self.preprocessed_select.value and datasets:
            self.preprocessed_select.value = [datasets[0].display_name]

        self._render_plots()

    def _set_status(self, message: str, level: str = "light") -> None:
        self.status.object = message
        self.status.alert_type = level

    def _handle_refresh(self, _event) -> None:
        self.refresh_catalog()
        self._set_status("Catalog refreshed.", "success")

    def _handle_preprocess(self, _event) -> None:
        selected_batches = [self.raw_by_label[label] for label in self.raw_select.value if label in self.raw_by_label]
        if not selected_batches:
            self._set_status("Select at least one raw batch before preprocessing.", "warning")
            return

        self.preprocess_button.disabled = True
        try:
            progress_messages: list[str] = []

            def update_progress(message: str) -> None:
                progress_messages.append(message)
                self._set_status("\n".join(progress_messages), "primary")

            preprocess_batches(
                selected_batches,
                output_dir=self.preprocessed_dir,
                progress_callback=update_progress,
            )
            self.refresh_catalog()
            new_labels = [
                dataset.display_name
                for dataset in self.preprocessed_by_label.values()
                if (dataset.product_id, dataset.timestamp) in {(batch.product_id, batch.timestamp) for batch in selected_batches}
            ]
            self.preprocessed_select.value = sorted(set(self.preprocessed_select.value + new_labels))
            self._set_status(f"Preprocessed {len(selected_batches)} batch(es).", "success")
        except Exception as error:
            self._set_status(f"Preprocess failed: {error}", "danger")
        finally:
            self.preprocess_button.disabled = False

    def _handle_selection_change(self, _event) -> None:
        self._render_plots()

    def _build_plot_pane(self, plot_type: str, locators: list[PlotDatasetLocator]):
        builder = PLOT_REGISTRY[plot_type].plot_builder
        plot = builder(locators)
        if isinstance(plot, Figure):
            return pn.pane.Plotly(plot, config={"responsive": True}, sizing_mode="stretch_width")
        return pn.pane.HoloViews(plot, sizing_mode="stretch_width")

    def _render_plots(self) -> None:
        selected_datasets = [self.preprocessed_by_label[label] for label in self.preprocessed_select.value if label in self.preprocessed_by_label]
        selected_plot_labels = self.plot_select.value

        if not selected_datasets:
            self.plot_area.objects = [pn.pane.Markdown("Select one or more preprocessed datasets to start plotting.")]
            return

        if not selected_plot_labels:
            self.plot_area.objects = [pn.pane.Markdown("Select at least one plot type.")]
            return

        product_ids = {dataset.product_id for dataset in selected_datasets}
        if len(product_ids) != 1:
            self.plot_area.objects = [pn.pane.Alert("Please select datasets from the same product for plotting.", alert_type="warning")]
            return

        locators = [dataset.to_locator(self.preprocessed_dir) for dataset in selected_datasets]
        plot_panes = []

        for plot_label in selected_plot_labels:
            plot_type = next(key for key, value in PLOT_LABELS.items() if value == plot_label)
            if any(plot_type not in dataset.available_views for dataset in selected_datasets):
                plot_panes.append(
                    pn.pane.Alert(
                        f"{plot_label} is unavailable because one or more selected datasets do not advertise that view.",
                        alert_type="warning",
                    )
                )
                continue

            try:
                plot_panes.append(self._build_plot_pane(plot_type, locators))
            except Exception as error:
                plot_panes.append(
                    pn.pane.Alert(
                        f"Failed to render {plot_label}: {error}",
                        alert_type="danger",
                    )
                )

        self.plot_area.objects = plot_panes or [pn.pane.Markdown("No plots are available for the current selection.")]

    def view(self):
        controls = pn.Column(
            "## Controls",
            self.preprocessed_select,
            self.raw_select,
            self.plot_select,
            self.preprocess_button,
            self.refresh_button,
            self.status,
            width=420,
            sizing_mode="stretch_height",
        )
        content = pn.Column(
            "## Visualization",
            self.plot_area,
            sizing_mode="stretch_both",
        )
        return pn.Row(controls, content, sizing_mode="stretch_both")


def build_app():
    hv.extension("bokeh")
    pn.extension("plotly")
    dashboard = OrderbookDashboard(RAW_DATA_DIR, PREPROCESSED_DIR)
    return dashboard.view()


def main() -> None:
    pn.serve(build_app, title="Orderbook Viewer", show=True)


if __name__ == "__main__":
    main()

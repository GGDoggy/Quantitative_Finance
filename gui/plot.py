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
)
from gui.registry import PLOT_LABELS, PLOT_REGISTRY
from gui.preprocess_service import preprocess_batches


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"


class OrderbookDashboard:
    def __init__(self, raw_dir: Path, preprocessed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.preprocessed_dir = preprocessed_dir
        self.preprocessed_by_label: dict[str, PreprocessedDataset] = {}
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
        self.refresh_button = pn.widgets.Button(
            name="Refresh Catalog",
            button_type="default",
            width=170,
        )
        self.preprocess_button = pn.widgets.Button(name="Preprocess Selected", button_type="primary", sizing_mode="stretch_width")
        self.dataset_summary = pn.pane.Markdown(
            "No dataset selected.",
            sizing_mode="stretch_width",
        )
        self.preprocess_progress = pn.pane.Markdown(
            "No preprocess job running.",
            sizing_mode="stretch_width",
        )
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
            self.preprocess_progress.object = "No preprocess job running."
            self._set_status("Select at least one raw batch before preprocessing.", "warning")
            return

        self.preprocess_progress.object = f"Queued {len(selected_batches)} raw batch(es) for preprocessing."
        self.preprocess_button.disabled = True
        try:
            progress_messages: list[str] = []

            def update_progress(message: str) -> None:
                progress_messages.append(message)
                progress_text = "\n".join(f"- {progress_message}" for progress_message in progress_messages)
                self.preprocess_progress.object = progress_text
                self._set_status(progress_text, "primary")

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
            self.preprocess_progress.object = f"Completed preprocessing {len(selected_batches)} batch(es)."
            self._set_status(f"Preprocessed {len(selected_batches)} batch(es).", "success")
        except Exception as error:
            self.preprocess_progress.object = f"Preprocess failed: {error}"
            self._set_status(f"Preprocess failed: {error}", "danger")
        finally:
            self.preprocess_button.disabled = False

    def _handle_selection_change(self, _event) -> None:
        self._render_plots()

    def _build_plot_pane(self, plot_type: str, locators: list[PlotDatasetLocator]) -> pn.viewable.Viewable:
        builder = PLOT_REGISTRY[plot_type].plot_builder
        plot = builder(locators)
        if isinstance(plot, Figure):
            return pn.pane.Plotly(plot, config={"responsive": True}, sizing_mode="stretch_width")
        return pn.pane.HoloViews(plot, sizing_mode="stretch_width")

    def _selected_datasets(self) -> list[PreprocessedDataset]:
        return [
            self.preprocessed_by_label[label]
            for label in self.preprocessed_select.value
            if label in self.preprocessed_by_label
        ]

    def _selected_plot_labels(self) -> list[str]:
        return [
            label
            for label in self.plot_select.value
            if label in PLOT_LABELS.values()
        ]

    def _update_dataset_summary(self, selected_datasets: list[PreprocessedDataset]) -> None:
        if not selected_datasets:
            self.dataset_summary.object = "No preprocessed dataset selected."
            return

        product_ids = sorted({dataset.product_id for dataset in selected_datasets})
        available_views = sorted(
            {PLOT_LABELS.get(view, view) for dataset in selected_datasets for view in dataset.available_views}
        )
        dataset_lines = "\n".join(
            f"- `{dataset.display_name}`"
            for dataset in selected_datasets
        )
        self.dataset_summary.object = (
            f"**Selected dataset count:** {len(selected_datasets)}\n\n"
            f"**Product ids:** {', '.join(product_ids)}\n\n"
            f"**Available advertised views:** {', '.join(available_views) or 'None'}\n\n"
            f"**Datasets**\n{dataset_lines}"
        )

    def _render_plots(self) -> None:
        selected_datasets = self._selected_datasets()
        selected_plot_labels = self._selected_plot_labels()
        self._update_dataset_summary(selected_datasets)

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

        locators: list[PlotDatasetLocator] = [
            dataset.to_locator(self.preprocessed_dir)
            for dataset in selected_datasets
        ]
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

    def build_header(self) -> pn.Row:
        title = pn.Column(
            "# Orderbook Dashboard",
            "Coinbase market data catalog, preprocessing, and interactive order book visualizations.",
            sizing_mode="stretch_width",
            margin=(0, 20, 0, 0),
        )
        return pn.Row(
            title,
            pn.Spacer(sizing_mode="stretch_width"),
            self.refresh_button,
            sizing_mode="stretch_width",
            align="center",
        )

    def build_dataset_section(self) -> pn.Card:
        return pn.Card(
            self.preprocessed_select,
            title="Dataset selection",
            collapsed=False,
            sizing_mode="stretch_width",
        )

    def build_sidebar(self) -> pn.Column:
        raw_batch_section = pn.Card(
            self.raw_select,
            self.preprocess_button,
            title="Raw batch preprocessing",
            collapsed=False,
            sizing_mode="stretch_width",
        )
        return pn.Column(
            "## Controls",
            self.build_dataset_section(),
            raw_batch_section,
            sizing_mode="stretch_height",
            width=420,
        )

    def build_plot_section(self) -> pn.Card:
        plot_controls = pn.Row(
            self.plot_select,
            sizing_mode="stretch_width",
        )
        summary = pn.Card(
            self.dataset_summary,
            title="Selected dataset summary",
            collapsed=False,
            sizing_mode="stretch_width",
        )
        workspace = pn.Card(
            self.plot_area,
            title="Plot workspace",
            collapsed=False,
            sizing_mode="stretch_both",
        )
        return pn.Card(
            "## Main workspace",
            plot_controls,
            summary,
            workspace,
            title="Visualization",
            collapsed=False,
            sizing_mode="stretch_both",
        )

    def build_status_section(self) -> pn.Card:
        return pn.Card(
            self.status,
            self.preprocess_progress,
            title="Status",
            collapsed=False,
            sizing_mode="stretch_width",
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
            main_layout=None,
        )


def build_app():
    hv.extension("bokeh")
    pn.extension("plotly")
    dashboard = OrderbookDashboard(RAW_DATA_DIR, PREPROCESSED_DIR)
    return dashboard.view()


def main() -> None:
    pn.serve(build_app, title="Orderbook Viewer", show=True)


if __name__ == "__main__":
    main()

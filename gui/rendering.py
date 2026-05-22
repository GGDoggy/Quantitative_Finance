"""Plot rendering, empty states, and render error presentation helpers."""

from __future__ import annotations

import math

import panel as pn
from plotly.graph_objects import Figure

from src.app_plot_registry import APP_PLOT_REGISTRY
from src.plots import PlotRenderOptions
from src.preprocess import PlotDatasetLocator, PreprocessedDataset

from .styles import (
    COST_FILTERED_PLOT_TYPES,
    PLOTLY_DARK_LAYOUT,
    SIMULATION_HEATMAP_PLOT_TYPES,
)


class DashboardRenderingMixin:
    """Build plot panes and render the active dashboard selection."""

    def _selected_cost(self) -> float:
        """Parse and validate the current cost input."""
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
        """Build the Panel pane for a plot type and dataset locator list."""
        builder = APP_PLOT_REGISTRY[plot_type].builder
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

    def _empty_state(self, message: str, level: str = "info") -> pn.pane.Alert:
        """Build a standard dashboard empty-state alert."""
        return pn.pane.Alert(message, alert_type=level, sizing_mode="stretch_width")

    def _render_error_alert(
        self, plot_label: str, error: Exception | None = None
    ) -> pn.pane.Alert:
        """Build the inline render-error alert for a plot card."""
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
        """Wrap plot output, metadata, and errors into a dashboard card."""
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
        """Build a warning card for unsupported dataset selections."""
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
        """Build the fallback card shown when plot rendering fails."""
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
        """Return the current empty-state alert, if rendering is not yet possible."""
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
        """Render the active plot selection into the dashboard workspace."""
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

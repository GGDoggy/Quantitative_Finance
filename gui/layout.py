"""Panel layout builders and reusable UI card helpers for the dashboard."""

from __future__ import annotations

import panel as pn

from .styles import COST_FILTERED_PLOT_TYPES, SIMULATION_HEATMAP_PLOT_TYPES


class DashboardLayoutMixin:
    """Build the visible dashboard layout from shared widgets and panes."""

    def _card(
        self,
        *objects,
        title: str,
        css_classes: list[str] | None = None,
        sizing_mode: str = "stretch_width",
        margin: tuple[int, int, int, int] = (0, 0, 18, 0),
    ) -> pn.Card:
        """Build a styled dashboard card."""
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
        """Build a standard section title and subtitle block."""
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
        """Build the dashboard header row."""
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
        """Build the dataset selection card."""
        return self._card(
            self.product_select,
            self.raw_dir_input,
            self.apply_raw_dir_button,
            self.dataset_summary,
            title="Dataset selection",
        )

    def build_sidebar(self) -> pn.Column:
        """Build the dashboard sidebar with preprocessing and simulation tools."""
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
        """Build the main visualization area and plot controls."""
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
        """Build the dashboard status card."""
        return self._card(
            self.status,
            title="Status",
            css_classes=["qf-status-card"],
        )

    def view(self):
        """Build and return the FastListTemplate dashboard view."""
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

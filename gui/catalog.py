"""Catalog discovery, selection helpers, and dataset/raw summary builders."""

from __future__ import annotations

from typing import Any

from src.app_plot_registry import (
    APP_PLOT_LABELS,
    get_dataset_plot_types,
    get_product_plot_types,
    supports_plot_type,
)
from src.preprocess import (
    PreprocessedDataset,
    discover_preprocessed_datasets,
    discover_raw_batches,
)
from src.preprocess.datasets import format_time_step, parse_timestamp

from .styles import SIMULATION_HEATMAP_PLOT_TYPES


class DashboardCatalogMixin:
    """Provide catalog refresh and option-building helpers for the dashboard."""

    @staticmethod
    def _plot_view_specs() -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple(
            (key, spec.required_payload_keys)
            for key, spec in PLOT_REGISTRY.items()
        )

    def refresh_catalog(self) -> None:
        """Reload raw batches and preprocessed datasets from the configured paths."""
        datasets = discover_preprocessed_datasets(
            self.preprocessed_dir,
            view_specs=self._plot_view_specs(),
        )
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
        if previous_product in product_options:
            next_product = previous_product
        elif "ETH-USD" in product_options:
            next_product = "ETH-USD"
        else:
            next_product = None
        product_select_options = self._with_placeholder_options(
            {product_id: product_id for product_id in product_options},
            self.PRODUCT_PLACEHOLDER,
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

    def _available_products(self) -> list[str]:
        """Return products that have at least one plottable dataset."""
        return sorted(
            {
                dataset.product_id
                for dataset in self.preprocessed_datasets
                if get_dataset_plot_types(dataset)
            }
        )

    def _selected_product(self) -> str | None:
        """Return the selected product identifier."""
        value = self.product_select.value
        return str(value) if value else None

    def _with_placeholder_options(
        self, options: dict[str, str], placeholder: str
    ) -> dict[str, str | None]:
        """Prepend a placeholder entry to widget options."""
        return {placeholder: None, **options}

    def _selectable_option_values(self, options: Any) -> set[str]:
        """Normalize widget options to a set of non-placeholder values."""
        if isinstance(options, dict):
            return {value for value in options.values() if value is not None}
        return {value for value in options if value is not None}

    def _selected_plot_type(self) -> str | None:
        """Return the registry plot type for the selected label."""
        value = self.plot_select.value
        if not value:
            return None
        try:
            return self._plot_type_for_label(str(value))
        except StopIteration:
            return None

    def _plot_label_for_type(self, plot_type: str) -> str:
        """Return the user-facing label for a plot type."""
        return APP_PLOT_LABELS.get(plot_type, plot_type)

    def _plot_type_for_label(self, plot_label: str) -> str:
        """Resolve a user-facing plot label back to its plot type."""
        return next(key for key, value in APP_PLOT_LABELS.items() if value == plot_label)

    def _datasets_for_product(self, product_id: str) -> list[PreprocessedDataset]:
        """Return all datasets belonging to the given product."""
        return [
            dataset
            for dataset in self.preprocessed_datasets
            if dataset.product_id == product_id
        ]

    def _available_plot_labels(self, product_id: str) -> list[str]:
        """Return enabled plot labels for a product in registry order."""
        return [
            self._plot_label_for_type(plot_type)
            for plot_type in get_product_plot_types(self._datasets_for_product(product_id))
        ]

    def _dataset_selection_key(self, dataset: PreprocessedDataset) -> str:
        """Return the widget selection key for a dataset."""
        return str(dataset.path)

    def _timestamp_option_label(self, dataset: PreprocessedDataset) -> str:
        """Build the user-facing timestamp label for a dataset option."""
        formatted_timestamp = parse_timestamp(dataset.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return f"{formatted_timestamp} | {format_time_step(dataset.time_step)}s"

    def _available_timestamp_options(
        self, product_id: str, plot_type: str
    ) -> dict[str, str]:
        """Return timestamp dropdown options for a product and plot type."""
        datasets_by_key: dict[str, PreprocessedDataset] = {}
        for dataset in self._datasets_for_product(product_id):
            if not supports_plot_type(dataset, plot_type):
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
        """Encode a simulation group key into a widget value."""
        product_id, time_step, time_step_token, signature = group_key
        token = time_step_token or format_time_step(time_step)
        return "|".join((product_id, token, signature))

    def _simulation_group_label(
        self,
        group_key: tuple[str, float, str | None, str],
        group: list[PreprocessedDataset],
    ) -> str:
        """Build the user-facing label for a simulation group."""
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
        """Return simulation-group dropdown options for heatmap plots."""
        simulation_datasets = [
            dataset
            for dataset in self._datasets_for_product(product_id)
            if any(supports_plot_type(dataset, view) for view in SIMULATION_HEATMAP_PLOT_TYPES)
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
        """Derive a grouping signature from a simulation filename."""
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
        """Return the normalized grouping key for a simulation dataset."""
        return (
            dataset.product_id,
            dataset.time_step,
            dataset.time_step_token,
            self._simulation_parameter_signature(dataset),
        )

    def _simulation_groups(
        self, datasets: list[PreprocessedDataset]
    ) -> dict[tuple[str, float, str | None, str], list[PreprocessedDataset]]:
        """Group simulation datasets by product, time step, and parameter signature."""
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
        """Return datasets implied by the current plot controls."""
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
                if supports_plot_type(dataset, plot_type)
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
            and supports_plot_type(dataset, plot_type)
        ]
        non_simulation_datasets = [
            dataset for dataset in matching_datasets if dataset.simulation_path is None
        ]
        if non_simulation_datasets:
            return [non_simulation_datasets[0]]
        return matching_datasets[:1]

    def _update_dataset_summary(self) -> None:
        """Refresh the dataset summary panel from current selections."""
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
            for plot_type in get_product_plot_types(product_datasets)
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
        """Refresh the raw-batch summary panel from current selections."""
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
        """Update controls to focus on a simulation-backed fill probability view."""
        if (
            dataset.product_id
            not in self._selectable_option_values(self.product_select.options)
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
        """Format a timestamp range for summary display."""
        if not timestamps:
            return "None"
        first = parse_timestamp(timestamps[0]).strftime("%Y-%m-%d %H:%M:%S")
        last = parse_timestamp(timestamps[-1]).strftime("%Y-%m-%d %H:%M:%S")
        if first == last:
            return first
        return f"{first} ~ {last}"

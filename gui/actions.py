"""Event handlers for refresh, preprocess, simulation, and control changes."""

from __future__ import annotations

from src.plots import PLOT_REGISTRY
from src.preprocess import PreprocessedDataset, preprocess_batches
from src.simulation import (
    list_algorithms,
    simulate_batches,
)

from .styles import COST_FILTERED_PLOT_TYPES, PLOT_PLACEHOLDER, SIMULATION_HEATMAP_PLOT_TYPES, TIMESTAMP_PLACEHOLDER, FILL_GROUP_PLACEHOLDER


class DashboardActionsMixin:
    """Handle UI events that mutate dashboard state or launch jobs."""

    def _handle_refresh(self, _event) -> None:
        """Reload raw and preprocessed catalogs from disk."""
        self.refresh_catalog()
        self._set_status(
            f"Catalog refreshed from raw directory: {self.raw_dir}", "success"
        )

    def _handle_apply_raw_dir(self, _event) -> None:
        """Validate and apply a new raw data directory."""
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
        """Toggle preprocess button and spinner state."""
        self.preprocess_button.disabled = is_loading
        self.preprocess_button.loading = is_loading
        self.preprocess_spinner.value = is_loading
        self.preprocess_spinner.visible = is_loading
        self.preprocess_progress.loading = is_loading

    def _set_simulation_loading(self, is_loading: bool) -> None:
        """Toggle simulation button and spinner state."""
        self.simulation_button.disabled = is_loading
        self.simulation_button.loading = is_loading
        self.simulation_spinner.value = is_loading
        self.simulation_spinner.visible = is_loading
        self.simulation_progress.loading = is_loading

    def _format_preprocess_progress(
        self, batch_count: int, progress_messages: list[str]
    ) -> str:
        """Build the preprocess progress markdown summary."""
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
        """Build the simulation progress markdown summary."""
        progress_lines = "\n".join(
            f"- {progress_message}" for progress_message in progress_messages
        )
        return (
            f"**Simulation batch count:** {batch_count}\n\n"
            f"**Progress**\n{progress_lines}"
        )

    def _handle_preprocess(self, _event) -> None:
        """Run preprocessing for the selected pending raw batches."""
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
                """Append a preprocess progress message to the UI."""
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
        """Run simulation for the selected raw batches."""
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
                """Append a simulation progress message to the UI."""
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
                1
                for simulation_result in simulation_results
                if simulation_result.overwritten
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
        """Update product, plot, and timestamp controls for a preprocessed dataset."""
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
        """Refresh plot choices when the selected product changes."""
        if self._updating_controls:
            return
        self._sync_plot_options(render=True)

    def _handle_plot_change(self, _event) -> None:
        """Refresh timestamp or simulation-group choices when plot changes."""
        if self._updating_controls:
            return
        self._sync_timestamp_options(render=True)

    def _handle_timestamp_change(self, _event) -> None:
        """Rerender plots after timestamp selection changes."""
        if self._updating_controls:
            return
        self._render_plots()

    def _handle_fill_group_change(self, _event) -> None:
        """Rerender plots after simulation group selection changes."""
        if self._updating_controls:
            return
        self._render_plots()

    def _handle_cost_change(self, _event) -> None:
        """Rerender cost-filtered plots after cost input changes."""
        if self._updating_controls:
            return
        if self._selected_plot_type() in COST_FILTERED_PLOT_TYPES:
            self._render_plots()

    def _handle_simulation_heatmap_setting_change(self, _event) -> None:
        """Persist valid heatmap setting edits and rerender the plot."""
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
        """Refresh raw batch summary after preprocess selection changes."""
        self._update_raw_summary()

    def _handle_simulation_raw_selection_change(self, _event) -> None:
        """Refresh raw batch summary after simulation selection changes."""
        self._update_raw_summary()

    def _handle_simulation_select_all(self, _event) -> None:
        """Select all discovered raw batches for simulation."""
        self.simulation_raw_select.value = list(self.all_raw_by_label.keys())

    def _handle_simulation_clear_selection(self, _event) -> None:
        """Clear the simulation raw batch selection."""
        self.simulation_raw_select.value = []

    def _handle_simulation_algorithm_change(self, _event) -> None:
        """Update algorithm-specific parameter visibility."""
        self._sync_simulation_parameter_visibility()

    def _sync_simulation_parameter_visibility(self) -> None:
        """Show controls supported by the currently registered simulation algorithms."""
        self.simulation_time_step_input.visible = bool(
            self.simulation_algorithm_select.value in list_algorithms()
        )

    def _sync_plot_options(self, *, render: bool) -> None:
        """Refresh plot dropdown options for the selected product."""
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
        """Refresh timestamp dropdown options for non-simulation plots."""
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
        """Refresh simulation-group dropdown options for heatmap plots."""
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
        """Toggle cost input visibility based on the selected plot type."""
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

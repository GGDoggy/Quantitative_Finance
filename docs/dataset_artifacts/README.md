# `src.dataset_artifacts`

`src.dataset_artifacts` 是 preprocessed / simulation `.npz` artifact 的唯一規則來源。

## Responsibilities

- artifact filename formatting
- artifact filename parsing
- artifact discovery
- artifact locator / metadata models

## Main APIs

- `format_time_step(...)`
- `format_resolved_time(...)`
- `parse_preprocessed_filename(...)`
- `parse_simulation_filename(...)`
- `build_preprocessed_output_path(...)`
- `build_simulation_output_path(...)`
- `discover_preprocessed_artifacts(...)`
- `discover_simulation_artifacts(...)`

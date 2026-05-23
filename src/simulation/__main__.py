from pathlib import Path

from .constants import (
    DATA_V3_PATH,
    DEFAULT_BASE_TICK,
    DEFAULT_RESOLVED_TIME,
    DEFAULT_TIME_STEP,
    OUTPUT_PATH,
)
from .io import build_output_path, parse_dataset_groups
from .models import RawSimulationDataset, SimulationRequest
from .runner import simulate_batch, simulate_batches
from .service import list_algorithms


def _dataset_output_path(
    dataset: RawSimulationDataset,
    output_path: Path | str,
    request: SimulationRequest,
) -> Path:
    return build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        request.time_step,
        request.algorithm,
        request.resolved_time,
    )


def _format_dataset_line(
    index: int,
    dataset: RawSimulationDataset,
    output_path: Path | str,
    request: SimulationRequest,
) -> str:
    output_file = _dataset_output_path(dataset, output_path, request)
    return f"[{index}] {dataset.file_stem} -> {output_file.name}"


def _is_processed(
    dataset: RawSimulationDataset,
    output_path: Path | str,
    request: SimulationRequest,
) -> bool:
    return _dataset_output_path(dataset, output_path, request).exists()


def _parse_selection(selection: str, item_count: int) -> list[int]:
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(item_count))

    chosen = []
    for token in selection.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"Invalid selection token: {token}")
        index = int(token) - 1
        if index < 0 or index >= item_count:
            raise ValueError(f"Selection out of range: {token}")
        chosen.append(index)

    if not chosen:
        raise ValueError("No dataset selected.")
    return sorted(set(chosen))


def prompt_algorithm_selection():
    algorithms = list_algorithms()
    print("Available simulation algorithms:")
    for index, algorithm_name in enumerate(algorithms, start=1):
        print(f"[{index}] {algorithm_name}")

    while True:
        raw = input("Algorithm: ").strip()
        if not raw.isdigit():
            print("Enter a number.")
            continue
        selected_index = int(raw) - 1
        if selected_index < 0 or selected_index >= len(algorithms):
            print("Selection out of range.")
            continue
        return algorithms[selected_index]


def prompt_dataset_selection(
    datasets: list[RawSimulationDataset],
    output_path: Path | str,
    request: SimulationRequest,
) -> list[RawSimulationDataset]:
    print("Available unprocessed datasets:")
    for index, dataset in enumerate(datasets, start=1):
        print(_format_dataset_line(index, dataset, output_path, request))
    print("Enter a number, comma-separated numbers, or 'all'.")

    while True:
        raw = input("Selection: ")
        try:
            selected_indices = _parse_selection(raw, len(datasets))
            return [datasets[index] for index in selected_indices]
        except ValueError as exc:
            print(exc)


def main(
    data_v3_path=DATA_V3_PATH,
    output_path=OUTPUT_PATH,
    time_step=DEFAULT_TIME_STEP,
    base_tick=DEFAULT_BASE_TICK,
):
    algorithm_name = prompt_algorithm_selection()
    request = SimulationRequest(
        algorithm=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=DEFAULT_RESOLVED_TIME,
    )
    datasets = parse_dataset_groups(data_v3_path)
    pending = [
        dataset
        for dataset in datasets
        if not _is_processed(dataset, output_path, request)
    ]

    if not pending:
        print("No unprocessed datasets found.")
        return

    selected = prompt_dataset_selection(pending, output_path, request)
    if len(selected) == 1:
        dataset = selected[0]
        print(f"Processing {dataset.file_stem} with {algorithm_name}...")
        output_file = simulate_batch(dataset, request, output_path).output_path
        print(f"Saved {output_file.name}")
        return

    print(f"Processing {len(selected)} datasets with {algorithm_name}...")
    results = simulate_batches(selected, request, output_path)
    print(f"Finished {len(results)} dataset(s).")


if __name__ == "__main__":
    main()

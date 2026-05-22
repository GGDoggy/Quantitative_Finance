from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.simulation import (  # noqa: E402
    DATA_V3_PATH,
    DEFAULT_BASE_TICK,
    DEFAULT_TIME_STEP,
    OUTPUT_PATH,
    list_algorithms,
    save_result,
    simulate_loaded_data,
)
from src.simulation.constants import DEFAULT_RESOLVED_TIME  # noqa: E402
from src.simulation.io import load_raw_dataset, parse_dataset_groups  # noqa: E402
from src.simulation.library import (  # noqa: E402
    get_default_worker_count,
    process_dataset_job,
)
from concurrent.futures import ProcessPoolExecutor, as_completed


def _parse_dataset_groups_legacy(data_v3_path):
    grouped = {}
    for path in sorted(Path(data_v3_path).glob("*.csv")):
        stem_parts = path.stem.split("-")
        if len(stem_parts) < 4:
            continue

        if stem_parts[0] == "level2" and stem_parts[-2] in {"init", "updates"}:
            data_type = stem_parts[-2]
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-2])
        elif stem_parts[0] == "trade":
            data_type = "trade"
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-1])
        else:
            continue

        key = (product_id, timestamp)
        grouped.setdefault(
            key,
            {
                "product_id": product_id,
                "timestamp": timestamp,
                "file_stem": f"{product_id}-{timestamp}",
            },
        )[data_type] = path

    available = []
    for dataset in grouped.values():
        if {"init", "updates", "trade"} <= dataset.keys():
            available.append(dataset)
    return sorted(available, key=lambda item: (item["product_id"], item["timestamp"]))


def _build_output_path(output_path, product_id, timestamp, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    filename = (
        f"{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}"
        f"-simulation-{algorithm_name}.npz"
    )
    return Path(output_path) / filename


def _is_processed(dataset, output_path, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    return _build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    ).exists()


def _format_dataset_line(index, dataset, output_path, time_step, algorithm_name, resolved_time=DEFAULT_RESOLVED_TIME):
    output_file = _build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return f"[{index}] {dataset.file_stem} -> {output_file.name}"


def _parse_selection(selection, item_count):
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


def prompt_dataset_selection(datasets, output_path, time_step, algorithm_name):
    print("Available unprocessed datasets:")
    for index, dataset in enumerate(datasets, start=1):
        print(_format_dataset_line(index, dataset, output_path, time_step, algorithm_name))
    print("Enter a number, comma-separated numbers, or 'all'.")

    while True:
        raw = input("Selection: ")
        try:
            selected_indices = _parse_selection(raw, len(datasets))
            return [datasets[index] for index in selected_indices]
        except ValueError as exc:
            print(exc)


def _process_dataset(dataset, output_path, algorithm_name, time_step, base_tick):
    loaded_data = load_raw_dataset(dataset)
    result = simulate_loaded_data(
        loaded_data,
        algorithm_name=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
    )
    return save_result(
        dataset,
        output_dir=output_path,
        algorithm_name=algorithm_name,
        time_step=time_step,
        result=result,
        base_tick=base_tick,
    )


def main(
    data_v3_path=DATA_V3_PATH,
    output_path=OUTPUT_PATH,
    time_step=DEFAULT_TIME_STEP,
    base_tick=DEFAULT_BASE_TICK,
):
    algorithm_name = prompt_algorithm_selection()
    datasets = parse_dataset_groups(data_v3_path)
    pending = [
        dataset
        for dataset in datasets
        if not _is_processed(dataset, output_path, time_step, algorithm_name)
    ]

    if not pending:
        print("No unprocessed datasets found.")
        return

    selected = prompt_dataset_selection(pending, output_path, time_step, algorithm_name)
    if len(selected) == 1:
        dataset = selected[0]
        print(f"Processing {dataset.file_stem} with {algorithm_name}...")
        output_file = _process_dataset(dataset, output_path, algorithm_name, time_step, base_tick)
        print(f"Saved {output_file}")
        return

    print(f"Processing {len(selected)} datasets with {algorithm_name}...")
    failures = []
    worker_count = get_default_worker_count(len(selected))
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(
                process_dataset_job,
                dataset,
                output_path,
                algorithm_name,
                time_step,
                base_tick,
            ): dataset
            for dataset in selected
        }
        for future in as_completed(future_to_dataset):
            dataset = future_to_dataset[future]
            try:
                job_result = future.result()
                print(f"Saved {job_result.output_file}")
            except Exception as exc:
                failures.append((dataset.file_stem, exc))
                print(f"Failed {dataset.file_stem}: {exc}")

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        print(f"Completed with failures: {failed_stems}")


if __name__ == "__main__":
    main()

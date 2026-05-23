from .compat import (
    format_dataset_line,
    get_algorithm_names,
    is_processed,
    parse_dataset_groups,
    parse_selection,
    run_datasets_in_parallel,
    run_dataset_simulation,
    save_simulation_npz,
)
from .constants import DATA_V3_PATH, DEFAULT_BASE_TICK, DEFAULT_TIME_STEP, OUTPUT_PATH


def prompt_algorithm_selection():
    algorithms = get_algorithm_names()
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
        print(format_dataset_line(index, dataset, output_path, time_step, algorithm_name))
    print("Enter a number, comma-separated numbers, or 'all'.")

    while True:
        raw = input("Selection: ")
        try:
            selected_indices = parse_selection(raw, len(datasets))
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
    datasets = parse_dataset_groups(data_v3_path)
    pending = [
        dataset
        for dataset in datasets
        if not is_processed(dataset, output_path, time_step, algorithm_name)
    ]

    if not pending:
        print("No unprocessed datasets found.")
        return

    selected = prompt_dataset_selection(pending, output_path, time_step, algorithm_name)
    if len(selected) == 1:
        dataset = selected[0]
        print(f"Processing {dataset['file_stem']} with {algorithm_name}...")
        result = run_dataset_simulation(dataset, algorithm_name, time_step, base_tick)
        output_file = save_simulation_npz(
            dataset,
            output_path,
            algorithm_name,
            time_step,
            base_tick,
            result,
        )
        print(f"Saved {output_file}")
        return

    print(f"Processing {len(selected)} datasets with {algorithm_name}...")
    run_datasets_in_parallel(selected, output_path, algorithm_name, time_step, base_tick)


if __name__ == "__main__":
    main()

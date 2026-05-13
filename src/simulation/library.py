from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path

import numpy as np

from .event_balanced_placeholder import (
    ALGORITHM_NAME as EVENT_BALANCED_PLACEHOLDER_NAME,
    simulate_virtual_best_orders as simulate_event_balanced_placeholder,
)
from .time_averaged_random_cancellation import (
    ALGORITHM_NAME as TIME_AVERAGED_RANDOM_CANCELLATION_NAME,
    file_time_to_unix,
    read_csv,
    simulate_virtual_best_orders as simulate_time_averaged_random_cancellation,
)


DATA_V3_PATH = Path("data/temp")
OUTPUT_PATH = Path("data/preprocessed")
DEFAULT_TIME_STEP = 0.01
DEFAULT_BASE_TICK = 0.00000001

SIMULATION_RESULT_KEYS = (
    "bid_prices",
    "bid_near_size",
    "bid_opp_size",
    "bid_survival_time",
    "bid_ahead",
    "bid_behind",
    "bid_vorder_ratio",
    "bid_result",
    "ask_prices",
    "ask_near_size",
    "ask_opp_size",
    "ask_survival_time",
    "ask_ahead",
    "ask_behind",
    "ask_vorder_ratio",
    "ask_result",
)

ALGORITHMS = {
    TIME_AVERAGED_RANDOM_CANCELLATION_NAME: simulate_time_averaged_random_cancellation,
    EVENT_BALANCED_PLACEHOLDER_NAME: simulate_event_balanced_placeholder,
}


def get_algorithm_names():
    return list(ALGORITHMS.keys())


def get_algorithm(name):
    try:
        return ALGORITHMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation algorithm: {name}") from exc


def parse_dataset_groups(data_v3_path):
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


def build_output_path(output_path, product_id, timestamp, time_step, algorithm_name):
    filename = f"{product_id}-{timestamp}-{time_step}-simulation-{algorithm_name}.npz"
    return Path(output_path) / filename


def is_processed(dataset, output_path, time_step, algorithm_name):
    return build_output_path(
        output_path,
        dataset["product_id"],
        dataset["timestamp"],
        time_step,
        algorithm_name,
    ).exists()


def load_dataset(dataset):
    init = read_csv(dataset["init"])
    updates = read_csv(dataset["updates"])
    trades = read_csv(dataset["trade"])
    start_time = file_time_to_unix(dataset["timestamp"])
    return init, updates, trades, start_time


def run_dataset_simulation(dataset, algorithm_name, time_step, base_tick):
    algorithm = get_algorithm(algorithm_name)
    init, updates, trades, start_time = load_dataset(dataset)
    return algorithm(
        init,
        updates,
        trades,
        start_time,
        time_step=time_step,
        base_tick=base_tick,
    )


def save_simulation_npz(dataset, output_path, algorithm_name, time_step, base_tick, result):
    output_file = build_output_path(
        output_path,
        dataset["product_id"],
        dataset["timestamp"],
        time_step,
        algorithm_name,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs = {
        "algorithm": algorithm_name,
        "product_id": dataset["product_id"],
        "file_stem": dataset["file_stem"],
        "time_step": time_step,
        "base_tick": base_tick,
    }
    save_kwargs.update(zip(SIMULATION_RESULT_KEYS, result))
    np.savez_compressed(output_file, **save_kwargs)
    return output_file


def format_dataset_line(index, dataset, output_path, time_step, algorithm_name):
    output_file = build_output_path(
        output_path,
        dataset["product_id"],
        dataset["timestamp"],
        time_step,
        algorithm_name,
    )
    return f"[{index}] {dataset['file_stem']} -> {output_file.name}"


def parse_selection(selection, item_count):
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


def get_default_worker_count(task_count):
    detected = os.cpu_count() or 1
    return max(1, min(task_count, detected))


def process_dataset_job(dataset, output_path, algorithm_name, time_step, base_tick):
    result = run_dataset_simulation(dataset, algorithm_name, time_step, base_tick)
    output_file = save_simulation_npz(
        dataset,
        output_path,
        algorithm_name,
        time_step,
        base_tick,
        result,
    )
    return {
        "file_stem": dataset["file_stem"],
        "output_file": str(output_file),
        "status": "saved",
    }


def run_datasets_in_parallel(selected, output_path, algorithm_name, time_step, base_tick):
    worker_count = get_default_worker_count(len(selected))
    failures = []
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
                print(f"Saved {job_result['output_file']}")
            except Exception as exc:
                print(f"Failed {dataset['file_stem']}: {exc}")
                failures.append((dataset["file_stem"], exc))

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        raise RuntimeError(f"Batch processing failed for: {failed_stems}")

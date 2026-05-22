from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path

from .constants import DEFAULT_RESOLVED_TIME
from .io import load_raw_dataset, parse_dataset_groups, save_result
from .models import RawSimulationDataset, SimulationRequest, SimulationWorkerPayload
from .runner import get_algorithm, get_algorithm_names, run_dataset_simulation


DATA_V3_PATH = Path("data/v3")
OUTPUT_PATH = Path("data/preprocessed")
DEFAULT_TIME_STEP = 0.01
DEFAULT_BASE_TICK = 0.00000001



def build_output_path(
    output_path,
    product_id,
    timestamp,
    time_step,
    algorithm_name,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    filename = (
        f"{product_id}-{timestamp}-{time_step}-resolved-{resolved_time}"
        f"-simulation-{algorithm_name}.npz"
    )
    return Path(output_path) / filename


def is_processed(
    dataset,
    output_path,
    time_step,
    algorithm_name,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    return build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    ).exists()




def save_simulation_npz(
    dataset,
    output_path,
    algorithm_name,
    time_step,
    base_tick,
    result,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    output_file = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return save_result(
        output_file,
        algorithm_name=algorithm_name,
        dataset=dataset,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
        result=result,
    )


def format_dataset_line(
    index,
    dataset,
    output_path,
    time_step,
    algorithm_name,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    output_file = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return f"[{index}] {dataset.file_stem} -> {output_file.name}"


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


def process_dataset_job(
    dataset,
    output_path,
    algorithm_name,
    time_step,
    base_tick,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    overwritten = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    ).exists()
    request = SimulationRequest(
        dataset=dataset,
        algorithm_name=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    loaded_data = load_raw_dataset(dataset)
    result = run_dataset_simulation(request, loaded_data)
    output_file = save_simulation_npz(
        dataset,
        output_path,
        algorithm_name,
        time_step,
        base_tick,
        result,
        resolved_time,
    )
    return SimulationWorkerPayload(
        file_stem=dataset.file_stem,
        output_file=str(output_file),
        overwritten=overwritten,
    )


def run_datasets_in_parallel(
    selected: list[RawSimulationDataset],
    output_path,
    algorithm_name,
    time_step,
    base_tick,
    resolved_time=DEFAULT_RESOLVED_TIME,
):
    normalized = [
        dataset
        if isinstance(dataset, RawSimulationDataset)
        else RawSimulationDataset(**dataset)
        for dataset in selected
    ]
    worker_count = get_default_worker_count(len(normalized))
    results = []
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
                resolved_time,
            ): dataset
            for dataset in normalized
        }
        for future in as_completed(future_to_dataset):
            dataset = future_to_dataset[future]
            try:
                job_result = future.result()
                results.append(job_result)
            except Exception as exc:
                failures.append((dataset.file_stem, exc))

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        raise RuntimeError(f"Batch processing failed for: {failed_stems}")

    return results

from pathlib import Path

from .constants import DEFAULT_RESOLVED_TIME
from .io import (
    build_output_path,
    load_raw_dataset,
    parse_dataset_groups,
    save_result_file,
)
from .models import RawSimulationDataset, SimulationRequest
from .registry import get_algorithm, list_algorithms
from .runner import (
    get_default_worker_count,
    process_dataset_job,
    run_datasets_in_parallel,
    run_simulation_request,
)


DATA_V3_PATH = Path("data/v3")
OUTPUT_PATH = Path("data/preprocessed")
DEFAULT_TIME_STEP = 0.01
DEFAULT_BASE_TICK = 0.00000001


def is_processed(
    dataset: RawSimulationDataset,
    output_path: Path | str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> bool:
    return build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    ).exists()


def save_simulation_npz(
    dataset: RawSimulationDataset,
    output_path: Path | str,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    result,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
):
    output_file = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return save_result_file(
        output_file,
        algorithm_name=algorithm_name,
        dataset=dataset,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
        result=result,
    )


def format_dataset_line(
    index: int,
    dataset: RawSimulationDataset,
    output_path: Path | str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
) -> str:
    output_file = build_output_path(
        output_path,
        dataset.product_id,
        dataset.timestamp,
        time_step,
        algorithm_name,
        resolved_time,
    )
    return f"[{index}] {dataset.file_stem} -> {output_file.name}"


def parse_selection(selection: str, item_count: int) -> list[int]:
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


def get_algorithm_names() -> list[str]:
    return list_algorithms()


def run_dataset_simulation(
    dataset: RawSimulationDataset,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
):
    request = SimulationRequest(
        algorithm_name=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    loaded_data = load_raw_dataset(dataset)
    return run_simulation_request(request, loaded_data)


def process_dataset_job_compat(
    dataset: RawSimulationDataset,
    output_path: Path | str,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
):
    request = SimulationRequest(
        algorithm_name=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    return process_dataset_job(dataset, output_path, request)


def run_datasets_in_parallel_compat(
    selected: list[RawSimulationDataset],
    output_path: Path | str,
    algorithm_name: str,
    time_step: float,
    base_tick: float,
    resolved_time: float = DEFAULT_RESOLVED_TIME,
):
    normalized = [
        dataset
        if isinstance(dataset, RawSimulationDataset)
        else RawSimulationDataset(**dataset)
        for dataset in selected
    ]
    request = SimulationRequest(
        algorithm_name=algorithm_name,
        time_step=time_step,
        base_tick=base_tick,
        resolved_time=resolved_time,
    )
    return run_datasets_in_parallel(normalized, output_path, request)

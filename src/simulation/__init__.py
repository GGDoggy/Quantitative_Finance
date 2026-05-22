from .best_size_changed import ALGORITHM_NAME as BEST_SIZE_CHANGED_NAME
from .constants import DEFAULT_RESOLVED_TIME
from .event_balanced import ALGORITHM_NAME as EVENT_BALANCED_NAME
from .library import DATA_V3_PATH, DEFAULT_BASE_TICK, DEFAULT_TIME_STEP, OUTPUT_PATH
from .models import (
    LoadedMarketData,
    RawSimulationDataset,
    SimulationJobResult,
    SimulationRequest,
    SimulationResult,
)
from .service import (
    list_algorithms,
    save_result,
    simulate_batch,
    simulate_batches,
    simulate_loaded_data,
)
from .time_averaged_random_cancellation import (
    ALGORITHM_NAME as TIME_AVERAGED_RANDOM_CANCELLATION_NAME,
)

# compat legacy API
from .compat import (
    build_output_path,
    format_dataset_line,
    get_algorithm,
    get_algorithm_names,
    is_processed,
    load_dataset,
    parse_dataset_groups,
    parse_selection,
    process_dataset_job,
    run_dataset_simulation,
    run_datasets_in_parallel,
    save_simulation_npz,
)

__all__ = [
    # new public API
    "list_algorithms",
    "simulate_loaded_data",
    "simulate_batch",
    "simulate_batches",
    "save_result",
    # dataclasses / types
    "LoadedMarketData",
    "RawSimulationDataset",
    "SimulationJobResult",
    "SimulationRequest",
    "SimulationResult",
    # constants
    "BEST_SIZE_CHANGED_NAME",
    "EVENT_BALANCED_NAME",
    "TIME_AVERAGED_RANDOM_CANCELLATION_NAME",
    "DATA_V3_PATH",
    "OUTPUT_PATH",
    "DEFAULT_BASE_TICK",
    "DEFAULT_TIME_STEP",
    "DEFAULT_RESOLVED_TIME",
    # compat
    "build_output_path",
    "format_dataset_line",
    "get_algorithm",
    "get_algorithm_names",
    "is_processed",
    "load_dataset",
    "parse_dataset_groups",
    "parse_selection",
    "process_dataset_job",
    "run_dataset_simulation",
    "run_datasets_in_parallel",
    "save_simulation_npz",
]

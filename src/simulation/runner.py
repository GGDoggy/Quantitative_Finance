from __future__ import annotations

from .best_size_changed import (
    ALGORITHM_NAME as BEST_SIZE_CHANGED_NAME,
    simulate_virtual_best_orders as simulate_best_size_changed,
)
from .event_balanced import (
    ALGORITHM_NAME as EVENT_BALANCED_NAME,
    simulate_virtual_best_orders as simulate_event_balanced,
)
from ._simulation_core import (
    ALGORITHM_NAME as TIME_AVERAGED_RANDOM_CANCELLATION_NAME,
    simulate_virtual_best_orders as simulate_time_averaged_random_cancellation,
)
from .models import LoadedMarketData, SimulationRequest, SimulationResult

ALGORITHMS = {
    TIME_AVERAGED_RANDOM_CANCELLATION_NAME: simulate_time_averaged_random_cancellation,
    EVENT_BALANCED_NAME: simulate_event_balanced,
    BEST_SIZE_CHANGED_NAME: simulate_best_size_changed,
}


def get_algorithm_names() -> list[str]:
    return list(ALGORITHMS.keys())


def get_algorithm(name):
    try:
        return ALGORITHMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation algorithm: {name}") from exc


def run_dataset_simulation(request: SimulationRequest, loaded_data: LoadedMarketData) -> SimulationResult:
    algorithm = get_algorithm(request.algorithm_name)
    init, updates, trades, start_time = loaded_data
    return algorithm(
        init,
        updates,
        trades,
        start_time,
        time_step=request.time_step,
        base_tick=request.base_tick,
        resolved_time=request.resolved_time,
    )

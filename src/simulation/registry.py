from __future__ import annotations

from collections.abc import Callable

from .best_size_changed import (
    ALGORITHM_NAME as BEST_SIZE_CHANGED_NAME,
    simulate_virtual_best_orders as simulate_best_size_changed,
)
from .event_balanced import (
    ALGORITHM_NAME as EVENT_BALANCED_NAME,
    simulate_virtual_best_orders as simulate_event_balanced,
)
from .time_averaged_random_cancellation import (
    ALGORITHM_NAME as TIME_AVERAGED_RANDOM_CANCELLATION_NAME,
    simulate_virtual_best_orders as simulate_time_averaged_random_cancellation,
)

SimulationAlgorithm = Callable[..., tuple]

ALGORITHMS: dict[str, SimulationAlgorithm] = {
    TIME_AVERAGED_RANDOM_CANCELLATION_NAME: simulate_time_averaged_random_cancellation,
    EVENT_BALANCED_NAME: simulate_event_balanced,
    BEST_SIZE_CHANGED_NAME: simulate_best_size_changed,
}


def list_algorithms() -> list[str]:
    return list(ALGORITHMS.keys())


def get_algorithm(name: str) -> SimulationAlgorithm:
    try:
        return ALGORITHMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation algorithm: {name}") from exc

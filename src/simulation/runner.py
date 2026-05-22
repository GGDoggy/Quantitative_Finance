from __future__ import annotations

from .models import LoadedMarketData, SimulationRequest, SimulationResult
from .library import get_algorithm


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

from pathlib import Path

import pytest

from src.preprocess.catalog import RawBatch
from src.simulation import simulate_batch, simulate_batches, simulate_loaded_data
from src.simulation.models import LoadedMarketData, SimulationRequest, SimulationResult, SimulationWorkerPayload


def _raw_batch(tmp_path: Path, timestamp: str = "20240101.010203") -> RawBatch:
    return RawBatch(
        product_id="ETH-USD",
        timestamp=timestamp,
        init_path=tmp_path / f"level2-ETH-USD-init-{timestamp}.csv",
        updates_path=tmp_path / f"level2-ETH-USD-updates-{timestamp}.csv",
        trade_path=tmp_path / f"trade-ETH-USD-{timestamp}.csv",
    )


def _loaded_data() -> LoadedMarketData:
    return LoadedMarketData(init=[[1.0]], updates=[[2.0]], trades=[[3.0]], start_time=0.0)


def _result() -> SimulationResult:
    values = tuple([float(index)] for index in range(26))
    return SimulationResult.from_algorithm_output(values)  # type: ignore[arg-type]


def test_simulate_loaded_data_validates_parameters() -> None:
    loaded_data = _loaded_data()

    with pytest.raises(ValueError, match="positive finite value"):
        simulate_loaded_data(loaded_data, algorithm_name="event_balanced", time_step=0.0)

    with pytest.raises(ValueError, match="non-negative finite value"):
        simulate_loaded_data(
            loaded_data,
            algorithm_name="event_balanced",
            time_step=0.01,
            resolved_time=-1.0,
        )


def test_simulation_request_validates_numeric_fields() -> None:
    with pytest.raises(ValueError, match="time_step must be a positive finite value"):
        SimulationRequest(algorithm="event_balanced", time_step=0.0, base_tick=1e-8, resolved_time=1.0)

    with pytest.raises(ValueError, match="resolved_time must be a non-negative finite value"):
        SimulationRequest(algorithm="event_balanced", time_step=0.01, base_tick=1e-8, resolved_time=-1.0)


def test_simulate_batch_runs_load_simulate_save_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_batch = _raw_batch(tmp_path)
    calls: list[str] = []

    def fake_load_raw_dataset(dataset):
        calls.append(f"load:{dataset.file_stem}")
        return _loaded_data()

    def fake_run_simulation_request(request, loaded_data):
        calls.append(f"simulate:{request.algorithm}")
        return _result()

    def fake_save_result(dataset, **kwargs):
        calls.append(f"save:{dataset.file_stem}")
        return kwargs["output_dir"] / "saved-file.npz"

    monkeypatch.setattr("src.simulation.service.load_raw_dataset", fake_load_raw_dataset)
    monkeypatch.setattr("src.simulation.service.run_simulation_request", fake_run_simulation_request)
    monkeypatch.setattr("src.simulation.service.save_result", fake_save_result)

    result = simulate_batch(
        raw_batch,
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.01,
    )

    assert result.output_path == tmp_path / "saved-file.npz"
    assert result.overwritten is False
    assert calls == [
        "load:ETH-USD-20240101.010203",
        "simulate:event_balanced",
        "save:ETH-USD-20240101.010203",
    ]
    assert result.dataset.file_stem == "ETH-USD-20240101.010203"


def test_simulate_batches_preserves_input_order_for_parallel_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = _raw_batch(tmp_path, "20240101.010203")
    second = _raw_batch(tmp_path, "20240101.010204")

    def fake_run_datasets_in_parallel(datasets, output_dir, request):
        assert request.algorithm == "event_balanced"
        return [
            SimulationWorkerPayload(
                file_stem=f"{second.product_id}-{second.timestamp}",
                output_file=str(output_dir / "second.npz"),
                overwritten=True,
            ),
            SimulationWorkerPayload(
                file_stem=f"{first.product_id}-{first.timestamp}",
                output_file=str(output_dir / "first.npz"),
                overwritten=False,
            ),
        ]

    monkeypatch.setattr("src.simulation.service.run_datasets_in_parallel", fake_run_datasets_in_parallel)

    results = simulate_batches(
        [first, second],
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.01,
    )

    assert [result.dataset.timestamp for result in results] == [
        "20240101.010203",
        "20240101.010204",
    ]
    assert [result.overwritten for result in results] == [False, True]
